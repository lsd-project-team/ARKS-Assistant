using System;
using System.Collections.Generic;
using System.Text;

namespace AKRS.Capacity.DB
{

    public class CapacityRecord : Record
    {
        Date _date;
        Time _time;
        int _count;

        /// <summary>
        /// 
        /// </summary>
        /// <param name="date">日期。</param>
        /// <param name="time">时间。</param>
        /// <param name="count">产量。</param>
        public CapacityRecord(Date date, Time time, int count)
            : base(new DateTime(date.Year, date.Month, date.Day, time.Hour, time.Minute, time.Second))
        {
            _date = date;
            _time = time;
            _count = count;
        }

        public CapacityRecord(CapacityRecord other)
            : base(other.DateTime)
        {
            if (other == null)
                throw new ArgumentNullException(nameof(other));

            _date = other._date;
            _time = other._time;
            _count = other._count;
        }

		public override string ToString()
		{
            return string.Format("date : {0}, time : {1}, count : {2}", _date, _time, _count);
		}

        public void Set(Date date, Time time, int count)
        {
            _date = date;
            _time = time;
            _count = count;
        }

        /// <summary>
        /// 日期。
        /// </summary>
        public Date Date
        {
            get { return _date; }
        }

        /// <summary>
        /// 时间。
        /// </summary>
        public Time Time
        {
            get { return _time; }
        }

        /// <summary>
        /// 产量。
        /// </summary>
        public int Count
        {
            get { return _count; }
        }
    }
}
