public class MaintenanceRecord
{
  public int MaintenanceRecordId { get; set; }
  public DateTime Date { get; set; }
  public string Description { get; set; }
  public int Cost { get; set; }

  public int VehicleId { get; set; }
  public Vehicle Vehicle { get; set; }
}