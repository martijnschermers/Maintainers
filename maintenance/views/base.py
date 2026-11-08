from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import Vehicle


class OwnerVehicleMixin(LoginRequiredMixin):
    model = Vehicle

    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user)
