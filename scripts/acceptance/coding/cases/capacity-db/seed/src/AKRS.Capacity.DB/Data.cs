using System;
using System.Collections.Generic;
using System.Text;
using System.Data.SQLite;
using System.Diagnostics;

namespace AKRS.Capacity.DB
{
	public class Data : IDisposable
	{
        private delegate void AddRecordFunc(Record record);


		SQLiteConnection _conn;
		SQLiteCommand _cmd;

        Dictionary<Type, AddRecordFunc> _addRecordDict;

		public Data(string databasePath)
		{
			Console.WriteLine("[Data::Data()] starts.");
			try
			{
				String s = String.Format("Data Source={0}", databasePath);
				_conn = new SQLiteConnection(s);
				_conn.Open();

				_cmd = _conn.CreateCommand();

                UpdateTables();

                _addRecordDict = new Dictionary<Type, AddRecordFunc>();
                _addRecordDict.Add(typeof(CapacityRecord), InsertOrReplaceCapacityRecord);
                _addRecordDict.Add(typeof(LogRecord), AddLogRecord);
                _addRecordDict.Add(typeof(ConfigRecord), InsertOrReplaceConfigRecord);
			}
			catch (Exception e)
			{
				if (_conn != null)
				{
					_conn.Close();
					_conn = null;
				}

				Console.WriteLine("[Data::Data()] {0}", e.Message);

				throw e;
			}
			finally
			{
				Console.WriteLine("[Data::Data()] ends.");
			}
		}

		public void Dispose()
		{
			if (_conn != null)
			{
				_conn.Close();
				_conn = null;
			}
		}


		private string[] GetTableNames()
		{
			_cmd.CommandText = "SELECT tbl_name FROM sqlite_master WHERE type='table';";
			_cmd.Parameters.Clear();

			List<string> list = new List<string>();
			using (SQLiteDataReader reader = _cmd.ExecuteReader())
			{
				while (reader.Read())
				{
					string name = reader.GetString(0);
					list.Add(name);
				}
			}

			return list.ToArray();
		}

		private void RenameTable(string name, string newName)
		{
			try
			{
				string cmdText = string.Format("ALTER TABLE {0} RENAME TO {1};", name, newName);
				_cmd.Parameters.Clear();
				_cmd.CommandText = cmdText;
				_cmd.ExecuteNonQuery();
			}
			catch (SQLiteException e)
			{
				Trace.WriteLine("[Data::RenameTable()] {0}.", e.Message);
				throw e;
			}
		}

		private void RenameTables()
		{
			string[] tableNames = this.GetTableNames();
			List<string> tableNameList = new List<string>(tableNames);

			if (tableNameList.Contains("Date") && !tableNameList.Contains("Capacity"))
				this.RenameTable("Date", "Capacity");

			if (tableNameList.Contains("Entry") && !tableNameList.Contains("Log"))
				this.RenameTable("Entry", "Log");
		}

        private void CreateTable_cap()
        {
            try
            {
                _cmd.Parameters.Clear();
                _cmd.CommandText = "CREATE TABLE IF NOT EXISTS cap('date' DATE, 'time' TIME, 'count' INT NOT NULL DEFAULT 0, PRIMARY KEY('date', 'time'))";
                _cmd.ExecuteNonQuery();
            }
            catch (SQLiteException e)
            {
                Trace.WriteLine("[Data::CreateTable_cap()] {0}", e.Message);
            }
        }

        private void FillTable_cap()
        {
            try
            {
                _cmd.Parameters.Clear();
                _cmd.CommandText = "INSERT INTO cap(date, time, count) SELECT DATE(date), TIME(date), count FROM Capacity";
                _cmd.ExecuteNonQuery();
            }
            catch (SQLiteException e)
            {
                Trace.WriteLine("[Data::FillTable_cap()] {0}", e.Message);
            }
        }

        private void CreateTable_config()
        {
            try
            {
                _cmd.Parameters.Clear();
                _cmd.CommandText = "CREATE TABLE IF NOT EXISTS config(key_index INT PRIMARY KEY, key TEXT UNIQUE, value TEXT NOT NULL)";
                _cmd.ExecuteNonQuery();
            }
            catch (SQLiteException exception)
            {
                Trace.WriteLine("[Data::CreateTable_config()] {0}", exception.Message);
            }
        }

        private void FillTable_config()
        {
            try
            {
                _cmd.Parameters.Clear();
                _cmd.CommandText = "INSERT OR REPLACE INTO config(key_index, key, value) VALUES(0, \'shift\', \'<Shift><Day start=\"07:30:00\" end=\"19:30:00\"/><Neight start=\"19:30:00\" end=\"07:30:00\"/></Shift>\')";
                _cmd.ExecuteNonQuery();
            }
            catch (SQLiteException exception)
            {
                Trace.WriteLine("[Data::FillTable_config()] {0}", exception.Message);
            }
        }

        private void ConstructNewTables()
        {
            string[] tableNames = this.GetTableNames();
			List<string> tableNameList = new List<string>(tableNames);

            if (!tableNameList.Contains("cap"))
            {
                //create table "cap", then fill it with the data of the table "Capacity".
                CreateTable_cap();

                if (tableNameList.Contains("Capacity"))
                {
                    FillTable_cap();
                }
            }

            if (!tableNameList.Contains("config"))
            {
                CreateTable_config();
                FillTable_config();
            }
        }

        private void UpdateTables()
        {
			// rename tables.
			this.RenameTables();

            // 
            ConstructNewTables();
        }

		const string SQL_INSERT_LOG_TABLE_FORMAT = @"
		    INSERT INTO Log(date, time, state, code, info) VALUES(@date, @time, @state, @code, @info)                    
		    ";

		private void AddLogRecord(Record record)
		{
            LogRecord logRecord = record as LogRecord;
            if (logRecord == null)
                throw new ArgumentException(nameof(record));

			try
			{
				string cmdText = SQL_INSERT_LOG_TABLE_FORMAT;
				string paramDate = record.DateTime.ToString("yyyy-MM-dd");
				string paramTime = record.DateTime.ToString("HH:mm:ss");
				string paramState = ((int)logRecord.State).ToString();
				string paramCode = logRecord.Code.ToString();
				string paramInfo = logRecord.Info;

				_cmd.Parameters.Clear();
				_cmd.CommandText = cmdText;
				_cmd.Parameters.AddWithValue("@date", paramDate);
				_cmd.Parameters.AddWithValue("@time", paramTime);
				_cmd.Parameters.AddWithValue("@state", paramState);
				_cmd.Parameters.AddWithValue("@code", paramCode);
				_cmd.Parameters.AddWithValue("@info", paramInfo);	// null is valid.
				_cmd.ExecuteNonQuery();
			}
			catch (SQLiteException e)
			{
				Trace.WriteLine("[Data::AddRecord(DetailRecord)] {0}.", e.Message);
				throw e;
			}
		}

		const string SQL_DELETE_LOG_TABLE_FORMAT = @"
            DELETE FROM Log WHERE id=@id
            ";

        /// <summary>
        /// 删除Log表中的指定记录。
        /// </summary>
        /// <param name="id">指定将要被删除的记录的id字段值。</param>
        public void RemoveLogRecord(int id)
        {
			try
			{
				string cmdText = SQL_DELETE_LOG_TABLE_FORMAT;			

				_cmd.Parameters.Clear();
				_cmd.CommandText = cmdText;
				_cmd.Parameters.AddWithValue("@id", id);
				_cmd.ExecuteNonQuery();
			}
			catch (SQLiteException e)
			{
				Trace.WriteLine("[Data::RemoveRecord(LogRecord)] {0}.", e.Message);
				throw e;
			}
        }

        //const string SQL_INSERT_CAPACITY_TABLE_FORMAT = @"
        //    INSERT INTO cap(date, time, count) VALUES(@date, @time, @count)
        //    ";

        //void AddRecord(CapacityRecord record)
        //{
        //    try
        //    {
        //        string cmdText = SQL_INSERT_CAPACITY_TABLE_FORMAT;

        //        _cmd.Parameters.Clear();
        //        _cmd.CommandText = cmdText;
        //        _cmd.Parameters.AddWithValue("@date", record.Date.ToString());
        //        _cmd.Parameters.AddWithValue("@time", record.Time.ToString());
        //        _cmd.Parameters.AddWithValue("@count", record.Count);

        //        _cmd.ExecuteNonQuery();
        //    }
        //    catch (SQLiteException e)
        //    {
        //        Trace.WriteLine("[Data::AddRecord(TotoalRecord)] {0}.", e.Message);
        //        throw e;
        //    }
        //}


        //const string SQL_UPDATE_CAPACITY_TABLE_FORMAT = @"
        //    UPDATE cap SET count=@count WHERE date=@date AND time=@time
        //    ";

        //private void UpdateRecord(CapacityRecord record)
        //{
        //    try
        //    {
        //        string cmdText = SQL_UPDATE_CAPACITY_TABLE_FORMAT;

        //        _cmd.Parameters.Clear();
        //        _cmd.CommandText = cmdText;
        //        _cmd.Parameters.AddWithValue("@count", record.Count);
        //        _cmd.Parameters.AddWithValue("@date", record.Date.ToString());
        //        _cmd.Parameters.AddWithValue("@time", record.Time.ToString());

        //        _cmd.ExecuteNonQuery();
        //    }
        //    catch (SQLiteException e)
        //    {
        //        Trace.WriteLine("[Data::UpdateRecord(TotoalRecord)] {0}.", e.Message);
        //        throw e;
        //    }
        //}


        const string SQL_INSERT_OR_REPLACE_CAPACITY_TABLE_FORMAT = @"
            INSERT OR REPLACE INTO cap(date, time, count) VALUES(@date, @time, @count)
            ";

        private void InsertOrReplaceCapacityRecord(Record record)
        {
            CapacityRecord capacityRecord = record as CapacityRecord;
            if (capacityRecord == null)
                throw new ArgumentException(nameof(record));

            try
            {
                _cmd.Parameters.Clear();
                _cmd.CommandText = SQL_INSERT_OR_REPLACE_CAPACITY_TABLE_FORMAT;
                _cmd.Parameters.AddWithValue("@count", capacityRecord.Count);
                _cmd.Parameters.AddWithValue("@date", capacityRecord.Date.ToString());
                _cmd.Parameters.AddWithValue("@time", capacityRecord.Time.ToString());

                _cmd.ExecuteNonQuery();
            }
            catch (SQLiteException e)
            {
                Trace.WriteLine("[Data::InsertOrReplaceRecord(TotoalRecord)] {0}.", e.Message);
                throw e;
            }
        }

        const string SQL_INSERT_OR_REPLACE_INTO_CONFIG_TABLE_FORMAT = @";
        INSERT OR REPLACE INTO config(key_index, key, value) VALUES(0, @key, @value)";
        
        private void InsertOrReplaceConfigRecord(Record record)
        {
            ConfigRecord configRecord = record as ConfigRecord;
            if (configRecord == null)
                throw new ArgumentException(nameof(record));

            try
            {
                _cmd.Parameters.Clear();
                _cmd.CommandText = SQL_INSERT_OR_REPLACE_INTO_CONFIG_TABLE_FORMAT;
                _cmd.Parameters.AddWithValue("@key", configRecord.Key);
                _cmd.Parameters.AddWithValue("@value", configRecord.Value);

                _cmd.ExecuteNonQuery();
            }
            catch (SQLiteException e)
            {
                Trace.WriteLine("[Data::InsertOrReplaceRecord(TotoalRecord)] {0}.", e.Message);
                throw e;
            }
        }

        public void AddRecord(Record record)
		{
            /*
			try
			{         
                if (record is CapacityRecord)
                {
                    try
                    {
                        this.AddRecord((CapacityRecord)record);
                    }
                    catch (SQLiteException e)
                    {
                        if (e.ResultCode == SQLiteErrorCode.Error) // SQL error or missing database
                        {
                            //this.CreateTotalTableIfNotExist();
                            //this.AddRecord(totalRecord);
                        }
                        else if (e.ResultCode == SQLiteErrorCode.Constraint)
                        {
                            this.UpdateRecord((CapacityRecord)record);
                        }
                    }
                }
                else if (record is LogRecord)
				{
					try
					{
						this.AddRecord((LogRecord)record);
					}
					catch (SQLiteException e)
					{
						if (e.ResultCode == SQLiteErrorCode.Error)// SQL error or missing database
						{
							//String tableName = String.Format("{0:D4}{1:D2}{2:D2}",
							//                                 detailRecord.DateTime.Year,
							//                                 detailRecord.DateTime.Month,
							//                                 detailRecord.DateTime.Day);
							//this.CreateDetailTable(tableName);
							//this.AddRecord(detailRecord);
						}
					}
				}
			}
			catch (Exception e)
			{
				Trace.WriteLine("[Data::AddRecord(Record)] {0}.", e.Message);
				throw e;
			}
            */

            try
            {
                /*
                CapacityRecord capacityRecord = record as CapacityRecord;
                if (capacityRecord != null)
                {
                    InsertOrReplaceRecord(capacityRecord);
                }
                else
                {
                    LogRecord logRecord = record as LogRecord;
                    if (logRecord != null)
                    {
                        AddRecord(logRecord);
                    }
                }
                */
         
                _addRecordDict[record.GetType()].Invoke(record);        
            }
            catch (SQLiteException)
            { }
            catch (Exception e)
            {
				Trace.WriteLine("[Data::AddRecord(Record)] {0}.", e.Message);
				throw e;
            }
		}




		const string FORMAT_READ_LOG_RECORD = @"
                SELECT id, time, state, code, info
				FROM Log
                WHERE date=@date
				ORDER BY time ASC
                ";

		public Record[] ReadRecord(LogRecord record)
		{
			Record[] recordArray = null;

			try
			{
				DateTime date = record.DateTime;
				string cmdText = FORMAT_READ_LOG_RECORD;
				string paramDate = record.DateTime.ToString("yyyy-MM-dd");

				_cmd.CommandText = cmdText;
				_cmd.Parameters.Clear();
				_cmd.Parameters.AddWithValue("@date", paramDate);

				List<Record> list = new List<Record>();
				using (SQLiteDataReader reader = _cmd.ExecuteReader())
				{
					while (reader.Read())
					{
                        int id = reader.GetInt32(0);
						string time = reader.GetString(1);
						LogRecord.STATE state = (LogRecord.STATE)reader.GetInt32(2);
						int error = reader.GetInt32(3);
						string info = null;
						if (!reader.IsDBNull(4))
							info = reader.GetString(4);

						DateTime dateTime = DateTime.Parse(paramDate + " " + time);

                        LogRecord logRecord = new LogRecord(id, dateTime, state, error, info);
                        list.Add(logRecord);
					}
				}

				recordArray = list.ToArray();
			}
			catch (SQLiteException e)
			{
				Trace.WriteLine("[Data::ReadRecord(DetailRecord)] {0}.", e.Message);
				throw e;
			}

			return recordArray;
		}

        const string FORMAT_READ_LOG_RECORDS = @"
            SELECT date, time, state, code, info
            FROM Log
            WHERE date>=@first_date AND date<=@last_date
                  AND info IS NOT NULL
            ORDER BY date ASC, time ASC
            ";

        LogRecord[] ReadRecords(LogRecord[] logRecords)
        {
            Debug.Assert(logRecords != null && logRecords.Length == 2);

            List<LogRecord> list = new List<LogRecord>();

            try
            {
                StringBuilder sb1 = new StringBuilder();

                _cmd.CommandText = FORMAT_READ_LOG_RECORDS;
                _cmd.Parameters.Clear();
                _cmd.Parameters.AddWithValue("@first_date", new Date(logRecords[0].DateTime));
                _cmd.Parameters.AddWithValue("@last_date", new Date(logRecords[1].DateTime));
                _cmd.ExecuteNonQuery();
                
                using (SQLiteDataReader reader = _cmd.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        var date = reader.GetDateTime(0);  // date
                        var time = reader.GetDateTime(1);  // time
                        DateTime dateTime = new DateTime(date.Year, date.Month, date.Day, time.Hour, time.Minute, time.Second);

                        var state = reader.GetInt32(2);     // state

                        var code = reader.GetInt32(3);      // code

                        var info = reader.GetString(4);    // info

                        list.Add(new LogRecord(dateTime, (LogRecord.STATE)state, code, info));
                    }
                }
            }
            catch (SQLiteException e)
            {
                Trace.WriteLine("[Data::ReadRecord(TotalRecord)] {0}.", e.Message);
                throw e;
            }

            return list.ToArray();
        }



        /* N天的产量。*/        
        const string FORMAT_READ_CAPACITY_RECORDS = @"
            /* N-days' dayshift count and neightshift count */
            SELECT date, SUM(dayshift_count), SUM(neightshift_count)
            FROM (
                    /* count of the dayshift */
                    SELECT date, SUM(count) AS dayshift_count, 0 AS neightshift_count
                    FROM cap
                    WHERE date IN ({0})
                          AND
                          time>=@dayshift_start_time
                          AND
                          time<@dayshift_end_time
                    GROUP BY date

                    UNION

                    /* neightshift count */
                    SELECT date, 0 AS dayshift_count, SUM(count) AS neightshift_count
                    FROM (
                           /* count of the first segment of the neightshift */
                           SELECT date, SUM(count) AS count 
                           FROM cap
                           WHERE date IN ({0})
                                 AND
                                 time>=@neightshift_start_time
                           GROUP BY date

                           UNION

                           /* count of the second segment of the neightshift */
                           SELECT DATE(date, '-1 days') AS date, SUM(count) AS count
                           FROM cap
                           WHERE date IN ({1})
                                 AND
                                 time<@neightshift_end_time
                           GROUP BY date
                         )
                     GROUP BY date
                 )
            GROUP BY date
            ";



        bool ReadRecords(CapacityRecordEx[] records)
        {
            Trace.Assert(records != null && records.Length > 0, "records != null && records.Length > 0");

            bool bResult = false;

            try
            {
                StringBuilder sb1 = new StringBuilder();
                StringBuilder sb2 = new StringBuilder();
                foreach (CapacityRecordEx record in records)
                {
                    sb1.AppendFormat("'{0}', ", record.DateTime.ToString("yyyy-MM-dd"));
                    sb2.AppendFormat("'{0}', ", record.DateTime.AddDays(1).ToString("yyyy-MM-dd"));
                }
                sb1.Length -= 2;
                sb2.Length -= 2;
                string cmdText = string.Format(FORMAT_READ_CAPACITY_RECORDS, sb1, sb2);

                Time dayshiftStartTime = records[0].DayshiftStartTime;
                Date dayshiftEndDate;
                Time dayshiftEndTime;
                records[0].GetDayshiftEndDateAndTime(out dayshiftEndDate, out dayshiftEndTime);

                Date neightshiftStartDate, neightshiftEndDate;
                Time neightshiftStartTime, neightshiftEndTime;
                records[0].GetNeightshiftStartDateAndTime(out neightshiftStartDate, out neightshiftStartTime);
                records[0].GetNeightshiftEndDateAndTime(out neightshiftStartDate, out neightshiftEndTime);

                _cmd.CommandText = cmdText;
                _cmd.Parameters.Clear();
                _cmd.Parameters.AddWithValue("@dayshift_start_time", dayshiftStartTime.ToString());
                _cmd.Parameters.AddWithValue("@dayshift_end_time", dayshiftEndTime.ToString());
                _cmd.Parameters.AddWithValue("@neightshift_start_time", neightshiftStartTime.ToString());
                _cmd.Parameters.AddWithValue("@neightshift_end_time", neightshiftEndTime.ToString());

                _cmd.ExecuteNonQuery();

                Dictionary<Date, DayShiftAndNeightShiftCount> dict = new Dictionary<Date, DayShiftAndNeightShiftCount>(records.Length);
                using (SQLiteDataReader reader = _cmd.ExecuteReader())
                {
                    try
                    {
                        while (reader.Read())
                        {
                            Date date = new Date(reader.GetDateTime(0));
                            int dayshiftCount = reader.GetInt32(1);
                            int neightshiftCount = reader.GetInt32(2);

                            dict.Add(date, new DayShiftAndNeightShiftCount(dayshiftCount, neightshiftCount));
                        }

                        bResult = true;
                    }
                    catch
                    {
                        bResult = false;
                    }
                }

                if (bResult)
                {
                    foreach (CapacityRecordEx record in records)
                    {
                        try
                        {
                            DayShiftAndNeightShiftCount dayShiftAndNeightShiftCount = dict[record.Date];
                            record.SetCount(dayShiftAndNeightShiftCount.DayshiftCount, dayShiftAndNeightShiftCount.NeightshiftCount);
                        }
                        catch
                        {
                            record.SetCount(0, 0);
                        }
                    }
                }
            }
            catch (SQLiteException e)
            {
                Trace.WriteLine("[Data::ReadRecord(TotalRecord)] {0}.", e.Message);
                throw e;
            }

            return bResult;
        }


        struct DayShiftAndNeightShiftCount
        {
            int _dayshiftCount;
            int _neightshiftCount;

            public DayShiftAndNeightShiftCount(int dayshiftCount, int neightshiftCount)
            {
                Debug.Assert(dayshiftCount >= 0 && neightshiftCount >= 0);

                _dayshiftCount = dayshiftCount;
                _neightshiftCount = neightshiftCount;
            }

            public int DayshiftCount { get { return _dayshiftCount; } }
            public int NeightshiftCount { get { return _neightshiftCount; } }
        }

        const string FORMAT_READ_CAPACITY_RECORD_EX = @"
            SELECT d.s, n.s
            FROM (
                    SELECT IFNULL(SUM(count), 0) AS s
                    FROM cap 
                    WHERE date=@first_day_date AND time>=@dayshift_start_time AND time<@dayshift_end_time
                 ) AS d
                 JOIN
                 (
                    SELECT IFNULL(SUM(count), 0) AS s
                    FROM cap
                    WHERE date=@first_day_date AND time>=@neightshift_start_time
                          OR
                          date=@second_day_date AND time <@neightshift_end_time
                 ) AS n
            ";

        bool ReadRecord(CapacityRecordEx record)
		{
			bool bResult = false;

			try
			{
				string cmdText = FORMAT_READ_CAPACITY_RECORD_EX;

                Date firstDayDate = record.Date;
                Date secondDayDate = firstDayDate.AddDays(1);
                Date dayshiftEndDate, neightshiftStartDate, neightshiftEndDate;
                Time dayshiftEndTime, neightshiftStartTime, neightshiftEndTime;
                record.GetDayshiftEndDateAndTime(out dayshiftEndDate, out dayshiftEndTime);
                record.GetNeightshiftStartDateAndTime(out neightshiftStartDate, out neightshiftStartTime);
                record.GetNeightshiftEndDateAndTime(out neightshiftEndDate, out neightshiftEndTime);

                string paramFirstDayDate = firstDayDate.ToString();
                string paramSecondDayDate = secondDayDate.ToString();
                string paramDayshiftStartTime = record.DayshiftStartTime.ToString();
                string paramDayshiftEndTime = dayshiftEndTime.ToString();

                string paramNeightshiftStartTime = neightshiftStartTime.ToString();
                string paramNeightshiftEndTime = neightshiftEndTime.ToString();

				_cmd.CommandText = cmdText;
				_cmd.Parameters.Clear();

                _cmd.Parameters.AddWithValue("@first_day_date", paramFirstDayDate);
                _cmd.Parameters.AddWithValue("@dayshift_start_time", paramDayshiftStartTime);
                _cmd.Parameters.AddWithValue("@dayshift_end_time", paramDayshiftEndTime);

                _cmd.Parameters.AddWithValue("@first_day_date", paramFirstDayDate);
                _cmd.Parameters.AddWithValue("@neightshift_start_time", paramNeightshiftStartTime);
                _cmd.Parameters.AddWithValue("@second_day_date", paramSecondDayDate);
                _cmd.Parameters.AddWithValue("@neightshift_end_time", paramNeightshiftEndTime);

				_cmd.ExecuteNonQuery();

				using (SQLiteDataReader reader = _cmd.ExecuteReader())
				{
					if (reader.Read())
					{                        
						int dayshiftCount = reader.GetInt32(0);
                        int neightshiftCount = reader.GetInt32(1);
                        record.SetCount(dayshiftCount, neightshiftCount);

						bResult = true;
					}
				}
			}
			catch (SQLiteException e)
			{
				Trace.WriteLine("[Data::ReadRecord(TotalRecord)] {0}.", e.Message);
				throw e;
			}

			return bResult;
		}


        const string FORMAT_READ_CONFIG_RECORD = @"SELECT value FROM config WHERE key = @key";

        private bool ReadRecord(ConfigRecord configRecord)
        {
			bool bResult = false;

			try
			{
				string cmdText = FORMAT_READ_CONFIG_RECORD;

				_cmd.CommandText = cmdText;
				_cmd.Parameters.Clear();

                _cmd.Parameters.AddWithValue("@key", configRecord.Key);

				_cmd.ExecuteNonQuery();

				using (SQLiteDataReader reader = _cmd.ExecuteReader())
				{
					if (reader.Read())
					{
                        configRecord.SetValue(reader.GetString(0));

						bResult = true;
					}
				}
			}
			catch (SQLiteException e)
			{
				Trace.WriteLine("[Data::ReadRecord(ConfigRecord)] {0}.", e.Message);
				throw e;
			}

			return bResult;
        }

		public Record[] GetRecord(Record record)
		{
			Record[] recordArray = null;

            if (record is CapacityRecordEx)
            {
                if (this.ReadRecord((CapacityRecordEx)record))
                    recordArray = new Record[] { record };
            }
			else if (record is LogRecord)
			{
				recordArray = this.ReadRecord((LogRecord)record);
			}
            else if (record is ConfigRecord)
            {
                ReadRecord((ConfigRecord)record);
                recordArray = new Record[] { record };
            }

			return recordArray;
		}


		public Record[] GetRecords(Record[] records)
		{
            CapacityRecordEx[] totalRecords = records as CapacityRecordEx[];
            if (totalRecords != null)
            {
                if (ReadRecords(totalRecords))
                    return totalRecords;
                else
                    return null;
            }
            else
            {
                LogRecord[] logRecords = records as LogRecord[];
                if (logRecords != null)
                {
                    return ReadRecords(logRecords);
                }
            }

			return null;
		}               

        public void BeginTransaction()
		{
			try
			{
				_cmd.Parameters.Clear();
				_cmd.CommandText = "BEGIN TRANSACTION"; 
				_cmd.ExecuteNonQuery();
			}
			catch (SQLiteException e)
			{
				Trace.WriteLine("[Data::BeginTransaction()] {0}.", e.Message);
				throw e;
			}
		}

		public void EndTransaction()
		{
			try
			{
				_cmd.Parameters.Clear();
				_cmd.CommandText = "END TRANSACTION";
				
				_cmd.ExecuteNonQuery();
			}
			catch (SQLiteException e)
			{
				Trace.WriteLine("[Data::EndTransaction()] {0}.", e.Message);
				throw e;
			}
		}



	}
}
