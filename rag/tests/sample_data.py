"""Deterministic sample content used to build document fixtures and assertions."""

PAGE_ONE_HEADING = "Photosynthesis converts light energy into chemical energy."
PAGE_ONE_BODY = (
    "The light-dependent reactions occur in the thylakoid membrane of "
    "the chloroplast."
)
PAGE_TWO_HEADING = "The Calvin cycle fixes carbon dioxide into glucose."
PAGE_TWO_BODY = "Carbon fixation takes place in the stroma of the chloroplast."

DOCX_PARAGRAPH = "Database normalization removes redundancy from relations."
DOCX_TABLE_ROWS = [
    ("Form", "Meaning"),
    ("1NF", "Atomic values"),
    ("2NF", "No partial dependency"),
    ("3NF", "No transitive dependency"),
]

SLIDE_ONE_LINES = ["Operating Systems", "A process is a program in execution."]
SLIDE_TWO_LINES = [
    "CPU Scheduling",
    "Round-robin scheduling gives each process a fixed time slice.",
]
SLIDE_TWO_NOTES = "Mention the ready queue and waiting queue."

TXT_CONTENT = (
    "Linear algebra studies vectors and linear transformations.\n\n"
    "A matrix represents a linear transformation between vector spaces."
)
