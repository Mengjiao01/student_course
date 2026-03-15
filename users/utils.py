def get_user_role(user):
    # Treat Django superusers as admins even if a profile record is missing.
    if user.is_superuser:
        return "admin"

    # Some test or seed users may not have a profile row yet.
    profile = getattr(user, "profile", None)
    if profile is None:
        return None

    return profile.role
