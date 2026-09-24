import logging
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django.conf import settings
from django.core.exceptions import ValidationError

from helpdesk.models import TicketAttachment

logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf', '.txt', '.docx', '.xlsx'}


def validate_uploads(files):
    if len(files) > settings.HELPDESK_MAX_FILES:
        raise ValidationError(f'Choose no more than {settings.HELPDESK_MAX_FILES} files at a time.')
    for upload in files:
        extension = Path(upload.name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValidationError('Allowed files: PNG, JPEG, PDF, TXT, DOCX, and XLSX.')
        if not upload.size or upload.size > settings.HELPDESK_MAX_FILE_SIZE:
            raise ValidationError(f'{upload.name}: file must be nonempty and no larger than {settings.HELPDESK_MAX_FILE_SIZE // (1024 * 1024)} MB.')
        try:
            header = upload.read(1024)
            valid = False
            if extension == '.png':
                valid = header.startswith(b'\x89PNG\r\n\x1a\n')
            elif extension in ('.jpg', '.jpeg'):
                valid = header.startswith(b'\xff\xd8\xff')
            elif extension == '.pdf':
                valid = header.startswith(b'%PDF-')
            elif extension == '.txt':
                upload.seek(0)
                content = upload.read().decode('utf-8-sig')
                valid = '\x00' not in content
            elif extension in ('.docx', '.xlsx'):
                upload.seek(0)
                with ZipFile(upload) as archive:
                    names = set(archive.namelist())
                    main = 'word/document.xml' if extension == '.docx' else 'xl/workbook.xml'
                    valid = '[Content_Types].xml' in names and main in names and not any(n.lower().endswith('vbaproject.bin') for n in names)
            if not valid:
                raise ValidationError(f'{upload.name}: contents do not match the file type.')
        except (BadZipFile, UnicodeDecodeError, RuntimeError, OSError) as exc:
            raise ValidationError(f'{upload.name}: unable to read this file type.') from exc
        finally:
            upload.seek(0)
    return files


def save_attachments(ticket, user, files, written, comment=None):
    for upload in files:
        attachment = TicketAttachment(ticket=ticket,
                                      comment=comment,
                                      uploader=user,
                                      original_name=Path(upload.name.replace('\\', '/')).name,
                                      size=upload.size)
        field = attachment._meta.get_field('file')
        name = field.generate_filename(attachment, upload.name)
        # Register the UUID destination before writing so interrupted writes are removed too.
        written.append((field.storage, name))
        stored_name = field.storage.save(name, upload, max_length=field.max_length)
        written[-1] = (field.storage, stored_name)
        attachment.file = stored_name
        attachment.save()


def cleanup_attachments(written):
    for storage, name in written:
        try:
            storage.delete(name)
        except OSError:
            logger.exception('Could not clean up failed attachment %s', name)
