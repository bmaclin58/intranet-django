// Unfold persists a previous "auto" theme even when THEME is set to "light".
// Set the approved brand theme before its deferred Alpine initialization.
try {
    localStorage.setItem('adminTheme', JSON.stringify('light'));
} catch (_) {
    // With storage unavailable, Unfold uses the configured light default.
}
