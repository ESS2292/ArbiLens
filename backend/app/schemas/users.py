from app.schemas.auth import OrganizationSummary, UserSummary


class CurrentUserResponse(UserSummary):
    organization: OrganizationSummary
