from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import TemplateView

from ..models import Transfer


class AccountDeleteView(LoginRequiredMixin, TemplateView):
    template_name = "maintenance/account_delete.html"

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            Transfer.objects.filter(from_user=request.user).delete()
            Transfer.objects.filter(to_user=request.user).delete()
            for vehicle in request.user.vehicles.all():
                vehicle.delete()
            request.user.delete()
        logout(request)
        return redirect("maintenance:home")
