using System;

namespace AKRS.Capacity.DB
{
	public enum RecordType
	{
		CapacityRecord,
        LogRecord,
        //YieldRecord
	}

    public class Record
    {
        public Record(DateTime dateTime)
        {
            this.DateTime = dateTime;
        }

		public override string ToString()
		{
			return this.DateTime.ToString();
		}

        public DateTime DateTime { get; set; }        
    }
}