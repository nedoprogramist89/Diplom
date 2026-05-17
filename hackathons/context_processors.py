from .permissions import can_create_hackathon


def hackathon_roles(request):
    return {
        'user_can_create_hackathon': (
            can_create_hackathon(request.user) if request.user.is_authenticated else False
        ),
    }
