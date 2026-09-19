"""Registry describing how each profile section identifies its entries.

A Salesforce profile is a flat list of repeated elements such as
<fieldPermissions> or <objectPermissions>. Inside each one, some child
elements *identify* the entry (the key) and the rest are the values we want
to compare (the attributes). This table records the key fields per section.
"""

NAMESPACE = "http://soap.sforce.com/2006/04/metadata"

# Synthetic section for top-level scalars like <custom>, <userLicense>.
SCALAR_SECTION = "_profile"

# Used to join the parts of a composite key for display and dict lookup.
KEY_SEPARATOR = " / "

KEY_FIELDS: dict[str, tuple[str, ...]] = {
    "applicationVisibilities": ("application",),
    "classAccesses": ("apexClass",),
    "customMetadataTypeAccesses": ("name",),
    "customPermissions": ("name",),
    "customSettingAccesses": ("name",),
    "externalDataSourceAccesses": ("externalDataSource",),
    "fieldPermissions": ("field",),
    "flowAccesses": ("flow",),
    "layoutAssignments": ("layout", "recordType"),
    "objectPermissions": ("object",),
    "pageAccesses": ("apexPage",),
    "recordTypeVisibilities": ("recordType",),
    "tabVisibilities": ("tab",),
    "userPermissions": ("name",),
}


def valid_section_names() -> list[str]:
    """Section names accepted by the CLI's --sections flag, sorted."""
    return sorted([*KEY_FIELDS, SCALAR_SECTION])
