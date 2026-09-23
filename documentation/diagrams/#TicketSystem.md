classDiagram
direction BT
class node0 {
   QuerySet ticketcomment_set
}
class node5
class node6
class node8 {
   ForeignKey comment
   DateTimeField created_at
   FileField file
   CharField original_name
   PositiveIntegerField size
   ForeignKey ticket
   ForeignKey uploader
}
class node9 {
   QuerySet attachments
   ForeignKey author
   TextField body
   DateTimeField created_at
   BooleanField internal
   ForeignKey ticket
}
class node2 {
   BooleanField active
   CharField description
   CharField name
   PositiveIntegerField position
   QuerySet ticket_set
}
class node4 {
   BooleanField active
   TextField choices
   CharField field_type
   CharField help_text
   CharField label
   PositiveIntegerField position
   BooleanField required
   ForeignKey ticket_type
}
class node3 {
   BooleanField active
   ForeignKey category
   CharField description
   CharField name
   PositiveIntegerField position
   QuerySet ticket_set
}
class node7 {
   JSONField answers
   ForeignKey assignee
   ForeignKey category
   CharField category_label
   DateTimeField closed_at
   QuerySet comments
   DateTimeField created_at
   TextField description
   CharField priority
   ForeignKey requester
   DateTimeField resolved_at
   CharField status
   CharField subject
   ForeignKey ticket_type
   CharField type_label
   DateTimeField updated_at
}
class node1

node0 "1" --* "1" node1 
node5 "1" --* "1" node6 
node8 "0..*" --* "1" node0 
node8 "1" --* "1" node5 
node8 "0..*" --* "1" node9 
node8 "0..*" --* "1" node7 
node9 "0..*" --* "1" node0 
node9 "1" --* "1" node5 
node9 "0..*" --* "1" node7 
node2 "1" --* "1" node5 
node4 "1" --* "1" node5 
node4 "0..*" --* "1" node3 
node3 "1" --* "1" node5 
node3 "0..*" --* "1" node2 
node7 "0..*" --* "1" node0 
node7 "1" --* "1" node5 
node7 "0..*" --* "1" node2 
node7 "0..*" --* "1" node3 
