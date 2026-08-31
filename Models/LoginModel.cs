using System.ComponentModel.DataAnnotations;

public class LoginModel
{
  [Required(ErrorMessage = "Username is required")]
  public string Username { get; set; } = string.Empty;

  [Required(ErrorMessage = "Password is required")]
  [DataType(DataType.Password)]
  public string Password { get; set; } = string.Empty;
}