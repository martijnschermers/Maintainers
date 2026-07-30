using Microsoft.EntityFrameworkCore;

public class VehicleContext : DbContext
{
  public VehicleContext(DbContextOptions<VehicleContext> options) : base(options)
  {
  }
  public DbSet<Vehicle> Vehicles { get; set; }
  public DbSet<MaintenanceRecord> MaintenanceRecords { get; set; }
}

public class Vehicle
{
  public int VehicleId { get; set; }
  public string Make { get; set; }
  public string Model { get; set; }
  public int Year { get; set; }

  public List<MaintenanceRecord> MaintenanceRecords { get; } = new();
}

public class MaintenanceRecord
{
  public int MaintenanceRecordId { get; set; }
  public DateTime Date { get; set; }
  public string Description { get; set; }

  public int VehicleId { get; set; }
  public Vehicle Vehicle { get; set; }
}