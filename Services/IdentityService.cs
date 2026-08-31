using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

public class IdentityService
{
  private readonly ApplicationDbContext _context;

  public IdentityService(ApplicationDbContext context)
  {
    _context = context;
  }

  public async Task<bool> CreateUserAsync(string username, string email, string password)
  {
    // Check if the user already exists
    if (await _context.Users.AnyAsync(u => u.UserName == username || u.Email == email))
    {
      return false; // User already exists
    }

    // Create a new user entity
    var user = new IdentityUser
    {
      UserName = username,
      Email = email,
      PasswordHash = HashPassword(password) // Implement your password hashing logic here
    };

    // Add the user to the database
    _context.Users.Add(user);
    await _context.SaveChangesAsync();

    return true; // User created successfully
  }

  private string HashPassword(string password)
  {
    // Implement your password hashing logic here (e.g., using BCrypt or another hashing algorithm)
    return password; // Placeholder, replace with actual hashing logic
  }

  public async Task<bool> AuthenticateUserAsync(string username, string password)
  {
    // Retrieve the user from the database
    var user = await _context.Users.FirstOrDefaultAsync(u => u.UserName == username);

    if (user == null)
    {
      return false; // User not found
    }

    // Verify the password (implement your password verification logic here)
    if (!VerifyPassword(password, user.PasswordHash))
    {
      return false; // Invalid password
    }

    return true; // Authentication successful
  }

  private bool VerifyPassword(string password, string hashedPassword)
  {
    // Implement your password verification logic here (e.g., using BCrypt or another hashing algorithm)
    return password == hashedPassword; // Placeholder, replace with actual verification logic
  }
}