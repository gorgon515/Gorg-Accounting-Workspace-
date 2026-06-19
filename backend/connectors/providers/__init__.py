"""Auto-import all providers so their @register_provider decorators run."""
from . import (
    sec_edgar, fred, federal_register, bls, yahoo_finance,
    additional_financial, workspace_connectors,
)
