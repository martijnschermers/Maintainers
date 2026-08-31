using Microsoft.EntityFrameworkCore;

public class DomainDbContext : DbContext
{
  public DomainDbContext(DbContextOptions<DomainDbContext> options) : base(options)
  {
  }
  public DbSet<Vehicle> Vehicles { get; set; }
  public DbSet<MaintenanceRecord> MaintenanceRecords { get; set; }
}