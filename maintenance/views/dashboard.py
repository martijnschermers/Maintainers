from django.db.models import Sum
from django.views.generic import TemplateView

from ..models import MaintenanceEntry, Vehicle


class HomeView(TemplateView):
    template_name = "maintenance/home.html"

    def get_template_names(self):
        if self.request.user.is_authenticated:
            return ["maintenance/dashboard.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            vehicles = Vehicle.objects.filter(owner=self.request.user)
            recent_entries = (
                MaintenanceEntry.objects.select_related("vehicle")
                .filter(vehicle__owner=self.request.user)
                .order_by("-performed_on", "-created_at")[:5]
            )
            total_cost = (
                MaintenanceEntry.objects.filter(vehicle__owner=self.request.user)
                .aggregate(total=Sum("total_cost"))["total"]
                or 0
            )
            context.update(vehicles=vehicles, recent_entries=recent_entries, total_cost=total_cost)
        return context
