from django.urls import path

from .views import (
    AccountDeleteView,
    AttachmentCreateView,
    HomeView,
    InvoiceAnalysisView,
    MaintenanceEntryCreateView,
    MaintenanceEntryDeleteView,
    MaintenanceEntryUpdateView,
    PublicTransferView,
    RdwLookupView,
    TransferAcceptView,
    TransferCreateView,
    UserDataExportView,
    VehicleCreateView,
    VehicleCsvExportView,
    VehicleDeleteView,
    VehicleDetailView,
    VehicleListView,
    VehiclePdfExportView,
    VehicleUpdateView,
)

app_name = "maintenance"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dashboard/", HomeView.as_view(), name="dashboard"),
    path("vehicles/", VehicleListView.as_view(), name="vehicle-list"),
    path("vehicles/new/", VehicleCreateView.as_view(), name="vehicle-create"),
    path("vehicles/<int:pk>/", VehicleDetailView.as_view(), name="vehicle-detail"),
    path("vehicles/<int:pk>/edit/", VehicleUpdateView.as_view(), name="vehicle-update"),
    path("vehicles/<int:pk>/delete/", VehicleDeleteView.as_view(), name="vehicle-delete"),
    path("vehicles/<int:vehicle_id>/entries/new/", MaintenanceEntryCreateView.as_view(), name="entry-create"),
    path("entries/<int:pk>/edit/", MaintenanceEntryUpdateView.as_view(), name="entry-update"),
    path("entries/<int:pk>/delete/", MaintenanceEntryDeleteView.as_view(), name="entry-delete"),
    path(
        "vehicles/<int:vehicle_id>/entries/analyze-invoice/",
        InvoiceAnalysisView.as_view(),
        name="invoice-analyze",
    ),
    path("entries/<int:entry_id>/attachments/new/", AttachmentCreateView.as_view(), name="attachment-create"),
    path("vehicles/<int:pk>/transfer/", TransferCreateView.as_view(), name="transfer-create"),
    path("transfer/<uuid:token>/", PublicTransferView.as_view(), name="transfer-public"),
    path("transfer/<uuid:token>/accept/", TransferAcceptView.as_view(), name="transfer-accept"),
    path("rdw/lookup/", RdwLookupView.as_view(), name="rdw-lookup"),
    path("vehicles/<int:pk>/export.csv", VehicleCsvExportView.as_view(), name="vehicle-export-csv"),
    path("vehicles/<int:pk>/export.pdf", VehiclePdfExportView.as_view(), name="vehicle-export-pdf"),
    path("account/export.json", UserDataExportView.as_view(), name="account-export"),
    path("account/delete/", AccountDeleteView.as_view(), name="account-delete"),
]
