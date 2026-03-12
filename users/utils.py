def get_user_role(user):
    if user.is_superuser:
        return "admin"

    profile = getattr(user, "profile", None)
    if profile is None:
        return None

    return profile.role
