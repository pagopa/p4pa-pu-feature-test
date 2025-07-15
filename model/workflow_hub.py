from enum import Enum


class WorkflowStatus(Enum):
    RUNNING = "WORKFLOW_EXECUTION_STATUS_RUNNING"
    COMPLETED = "WORKFLOW_EXECUTION_STATUS_COMPLETED"
    CANCELED = "WORKFLOW_EXECUTION_STATUS_CANCELED"
    TERMINATED = "WORKFLOW_EXECUTION_STATUS_TERMINATED"
    FAILED = "WORKFLOW_EXECUTION_STATUS_FAILED"


class WorkflowType(Enum):
    SYNC_ACA = "SynchronizeSyncAcaWF"
    ASYNC_GPD = "SynchronizeAsyncGpdWF"
    EXPIRATION_DP = "CheckDebtPositionExpirationWF"
    IUD_CLASSIFICATION = "IudClassificationWF"
    IUF_CLASSIFICATION = "IufClassificationWF"
    TRANSFER_CLASSIFICATION = "TransferClassificationWF"
    PAYMENTS_REPORTING_INGESTION = "PaymentsReportingIngestionWF"
    TREASURY_OPI_INGESTION = "TreasuryOpiIngestionWF"
    SEND_NOTIFICATION_PROCESS = "SendNotificationProcessWF"
    SEND_NOTIFICATION_DATE_RETRIEVE = "SendNotificationDateRetrieveWF"
    DEBT_POSITION_INGESTION_FLOW = "DebtPositionIngestionFlowWF"
    CREATE_ASSESSMENT = "CreateAssessmentsWF"
