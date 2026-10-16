from enum import Enum

class SendCampaignCounter(Enum):
    TOTAL = 'total'
    ACCEPTED = 'accepted'
    DELIVERED = 'delivered'
    COMPLETED = 'completed'
    ANALOGIC_COMPLETION_PRE_OUTCOME = 'analogicCompletionPreOutcome'
    ANALOGIC_COMPLETION = 'analogicCompletion'
    DIGITAL_COMPLETION_DIGITAL_DOMICILE = 'digitalCompletionDigitalDomicile'
    DIGITAL_COMPLETION_COURTESY_MESSAGE = 'digitalCompletionCourtesyMessage'
    FAILED = 'failed'
    DECEASED_RECIPIENT = 'deceasedRecipient'
    RECIPIENT_NOT_FOUND = 'recipientNotFound'
    PAID = 'paid'