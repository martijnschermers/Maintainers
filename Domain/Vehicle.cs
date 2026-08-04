public class Vehicle
{
  public int VehicleId { get; set; }
  public string Make { get; set; }
  public string Model { get; set; }
  public int Year { get; set; }
  public string Type { get; set; }
  public int? Mileage { get; set; }
  public string? LicensePlate { get; set; }

  public List<MaintenanceRecord> MaintenanceRecords { get; } = new();
}
