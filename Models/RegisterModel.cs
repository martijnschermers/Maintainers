using System.ComponentModel.DataAnnotations;

namespace Maintainers.Models;

public class RegisterModel
{
  [Required(ErrorMessage = "Username is required")]
  public string Username { get; set; } = string.Empty;

  [Required(ErrorMessage = "Email is required")]
  [EmailAddress(ErrorMessage = "Invalid email address")]
  public string Email { get; set; } = string.Empty;

  [Required(ErrorMessage = "Password is required")]
  [DataType(DataType.Password)]
  public string Password { get; set; } = string.Empty;

  [Required(ErrorMessage = "Confirm password is required")]
  [DataType(DataType.Password)]
  [Compare("Password", ErrorMessage = "Passwords do not match")]
  public string ConfirmPassword { get; set; } = string.Empty;
}