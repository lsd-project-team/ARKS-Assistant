using System;
using System.Collections.Generic;
using System.Text;
using System.Data.SQLite;

namespace AKRS.Capacity.DB
{
	public class ErrorCode : IDisposable
	{
		const string FORMAT = @"SELECT name, desc FROM Errors WHERE code={0}";


		string _strDbPath;
		SQLiteConnection _conn;
		SQLiteCommand _cmd;

		public ErrorCode(string dbPath)
		{
			_strDbPath = dbPath;

			SQLiteConnectionStringBuilder sb = new SQLiteConnectionStringBuilder();
			sb.DataSource = _strDbPath;

			_conn = new SQLiteConnection(sb.ConnectionString);
			_conn.Open();

			_cmd = _conn.CreateCommand();
		}

		public void Dispose()
		{
			if (_conn != null)
			{
				_conn.Close();
				_conn = null;
			}
		}


		public void GetInfo(int errorCode, out string name, out string desc)
		{
			_cmd.CommandText = string.Format(FORMAT, errorCode);
			using (SQLiteDataReader reader = _cmd.ExecuteReader())
			{
				if (reader.Read())
				{
					name = reader.GetString(0);
					desc = reader.GetString(1);
				}
				else
				{
					throw new CodeNotFoundException(errorCode);
				}
			}
		}
	}
}
