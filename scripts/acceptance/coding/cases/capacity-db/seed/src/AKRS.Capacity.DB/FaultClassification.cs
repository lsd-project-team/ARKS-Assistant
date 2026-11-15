using System;
using System.Collections.Generic;
using System.Text;
using System.Data.SQLite;

namespace AKRS.Capacity.DB
{
	public class FaultClassification
	{
		SQLiteConnection _conn;
		SQLiteCommand _cmd;

		Dictionary<string, Classification> _dictInfo;
		Dictionary<int, string> _dictClass;
		Dictionary<int, string> _dictCategory;

		public FaultClassification(string dbPath)
		{
			try
			{
				String s = String.Format("Data Source={0}", dbPath);
				_conn = new SQLiteConnection(s);
				_conn.Open();

				_cmd = _conn.CreateCommand();

				_dictInfo = new Dictionary<string, Classification>();
				_dictClass = new Dictionary<int, string>();
				_dictCategory = new Dictionary<int, string>();

				this.RefreshDictionaries();
			}
			catch (Exception e)
			{
				if (_conn != null)
				{
					_conn.Close();
					_conn = null;
				}

				throw e;
			}
			finally
			{ }
		}

		public void Dispose()
		{
			if (_conn != null)
			{
				_conn.Close();
				_conn = null;
			}
		}

		public void RefreshDictionaries()
		{
			this.RefreshDictionaryInfo();
			this.RefreshDictionaryClass();
			this.RefreshDictionaryCategory();
		}

		public int CategoryCount
		{
			get { return _dictCategory.Count; }
		}

		public int ClassCount
		{
			get { return _dictClass.Count; }
		}

		public int InfoCount
		{
			get { return _dictInfo.Count; }
		}
		
		public bool GetClassCategory(string s, out int iClass, out int iCategory)
		{
			bool bResult = false;
			try
			{
				iClass = _dictInfo[s].Class;
				iCategory = _dictInfo[s].Category;
				bResult = true;
			}
			catch
			{
				iClass = 0;
				iCategory = 0;
				bResult = false;
			}
			return bResult;
		}

		public string GetClassName(int iClass)
		{
			string name = null;
			try
			{
				name = _dictClass[iClass];
			}
			catch
			{ }
			return name;
		}

		public string GetCategoryName(int iCategory)
		{
			string name = null;
			try
			{
				name = _dictCategory[iCategory];
			}
			catch
			{ }
			return name;
		}


		void RefreshDictionaryInfo()
		{
			_cmd.CommandText = "SELECT name, class, category FROM Info " +
								"WHERE	Info.class IS NOT NULL " +
								"AND " +
								"Info.category IS NOT NULL ";
			_cmd.Parameters.Clear();

			_dictInfo.Clear();
			using (SQLiteDataReader reader = _cmd.ExecuteReader())
			{
				while (reader.Read())
				{
					string name = reader.GetString(0);
					int iClass = reader.GetInt32(1);
					int iCategory = reader.GetInt32(2);
					_dictInfo.Add(name, new Classification(iClass, iCategory));
				}
			}
		}


		void RefreshDictionaryClass()
		{
			_cmd.CommandText = "SELECT id, name, desc FROM Class";
			_cmd.Parameters.Clear();

			_dictClass.Clear();
			using (SQLiteDataReader reader = _cmd.ExecuteReader())
			{
				while (reader.Read())
				{
					int id = reader.GetInt32(0);
					string name;
					if (reader.IsDBNull(2))
						name = reader.GetString(1);
					else
						name = reader.GetString(2);

					_dictClass.Add(id, name);
				}
			}
		}

		void RefreshDictionaryCategory()
		{
			_cmd.CommandText = "SELECT id, name, desc FROM Category";
			_cmd.Parameters.Clear();

			_dictCategory.Clear();
			using (SQLiteDataReader reader = _cmd.ExecuteReader())
			{
				while (reader.Read())
				{
					int id = reader.GetInt32(0);
					string name;
					if (reader.IsDBNull(2))
						name = reader.GetString(1);
					else
						name = reader.GetString(2);

					_dictCategory.Add(id, name);
				}
			}
		}


	}
}
