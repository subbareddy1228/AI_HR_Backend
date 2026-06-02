# CONTACT SCHEMAS
from .contact import (
    ContactBase,
    ContactCreate,
    ContactUpdate,
    ContactResponse,
)

# COMPANY SCHEMAS
from .company import (
    CompanyBase,
    CompanyCreate,
    CompanyResponse,
)

# DEAL SCHEMAS
from .deal import (
    DealBase,
    DealCreate,
    DealUpdate,
    DealOut,
)

# PIPELINE SCHEMAS
from .pipeline import (
    StatusEnum,
    PipelineBase,
    PipelineCreate,
    PipelineResponse,
)

# ACTIVITY SCHEMAS
from .activity import (
    ActivityBase,
    ActivityCreate,
    ActivityUpdate,
    Activity,
)

# LEAD SCHEMAS
from .lead import (
    LeadBase,
    LeadCreate,
    LeadUpdate,
    LeadRead,
)

# ANALYTICS SCHEMAS (stays in lead.py? or analytics.py? depends on your structure)
from .analytics import (
    StageSummary,
    SourceBreakdown,
)
