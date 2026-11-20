using System;
using System.Data.SqlClient;
namespace App {
  public class Login {
    string password = "Sup3rSecret!";
    public void Go(string user) {
      var cn = new SqlConnection("Server=.;Database=x;User Id=sa;Password=abc123;");
      string sql = "SELECT * FROM Users WHERE name='" + user + "'";
      var s2 = $"DELETE FROM T WHERE id={user}";
      try { cn.Open(); } catch (Exception ex) { }
      // TODO: fix this
      string url = "http://x.com/a(b";   // paren in string ok
      var v = @"C:\path\"; 
      if (user == null) {
        Console.WriteLine("hi");
      throw ex;
    }
  }
}
