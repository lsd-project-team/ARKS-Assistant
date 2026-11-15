using System;
using System.Collections.Generic;
using System.Text;

namespace AKRS.Capacity.DB
{
	public class LogRecord : Record
	{
		public enum STATE
		{
			Undefined = -1,
			Stopped = 0,
			Waiting = 1,
			Running = 2
		}

        public LogRecord(DateTime dateTime, STATE state, int code, string info)
            : this(-1, dateTime, state, code, info)
		{}

		public LogRecord(int id, DateTime dateTime, STATE state, int code, string info)
			: base(dateTime)
		{
            m_id = id;

			this.State = state;
			this.Code = code;
			this.Info = info;
		}

		public override string ToString()
		{
            StringBuilder sb = new StringBuilder();
            if (m_id >= 0)
                sb.AppendFormat("ID : {0}, ", m_id);

            sb.AppendFormat("dateTime : {0}, state : {1}, code : {2}, info : {3}",
				this.DateTime.ToString("yyyy-MM-dd HH:mm:ss"),
				(int)this.State,
				this.Code,
				this.Info);

            return sb.ToString();
		}

        int m_id;

        public int Id
        {
            get
            {
                if (m_id < 0)
                    throw new IdNotInitializedException();
                else
                    return m_id;
            }
        }

		public STATE State { get; set; }
		public int Code { get; set; }
		public string Info { get; set; }

        public bool IdValid
        {
            get { return m_id >= 0; }
        }
	}
}
