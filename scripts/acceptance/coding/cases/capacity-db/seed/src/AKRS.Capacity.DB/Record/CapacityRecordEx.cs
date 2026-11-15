using System;
using System.Collections.Generic;
using System.Text;

namespace AKRS.Capacity.DB
{

    public class CapacityRecordEx : Record
    {
        readonly Date _date;
        readonly Time _dayshiftStartTime;
        readonly int _shiftMinutes;

        int _dayshiftCount;
        int _neightshiftCount;

        /// <summary>
        /// 
        /// </summary>
        /// <param name="date">日期。</param>
        /// <param name="dayshiftStartTime">白班的开始时间。</param>
        /// <param name="shiftMinutes">白/夜班的时长，单位是分钟。</param>
        /// <param name="dayshiftCount">白班的产量。</param>
        /// <param name="neightshiftCount">夜班的产量。</param>
        public CapacityRecordEx(Date date, Time dayshiftStartTime, int shiftMinutes,  int dayshiftCount, int neightshiftCount)
            : base((DateTime)date)
        {
            _date = date;
            _dayshiftStartTime = dayshiftStartTime;
            _shiftMinutes = shiftMinutes;
            _dayshiftCount = dayshiftCount;
            _neightshiftCount = neightshiftCount;
        }

        public CapacityRecordEx(Date date, Time dayshiftStartTime, int shiftMinutes)
            : this(date, dayshiftStartTime, shiftMinutes, 0, 0)
        { }

        public CapacityRecordEx(CapacityRecordEx other)
            : base(other.DateTime)
        {
            _dayshiftStartTime = other._dayshiftStartTime;
            _shiftMinutes = other._shiftMinutes;
            _dayshiftCount = other._dayshiftCount;
            _neightshiftCount = other._neightshiftCount;
        }

		public override string ToString()
		{
			return string.Format("date : {0}, count : {1} / {2}", this.DateTime.ToString("yyyy-MM-dd"), _dayshiftCount, _neightshiftCount);
		}

        /// <summary>
        /// 设置白班和夜班的产量。
        /// </summary>
        /// <param name="dayshiftCount"></param>
        /// <param name="neightshiftCount"></param>
        public void Set(int dayshiftCount, int neightshiftCount)
        {
            if (dayshiftCount < 0)
                throw new ArgumentOutOfRangeException(nameof(dayshiftCount));

            if (neightshiftCount < 0)
                throw new ArgumentOutOfRangeException(nameof(neightshiftCount));

            _dayshiftCount = dayshiftCount;
            _neightshiftCount = neightshiftCount;
        }

        /// <summary>
        /// 日期。
        /// </summary>
        public Date Date
        {
            get { return _date; }
        }

        /// <summary>
        /// 白班的开始时间。
        /// </summary>
        public Time DayshiftStartTime
        {
            get { return _dayshiftStartTime; }
        }

        /// <summary>
        /// 获取白班的结束日期和时间。
        /// </summary>
        /// <param name="dayshiftEndDate"></param>
        /// <param name="dayshiftEndTime"></param>
        public void GetDayshiftEndDateAndTime(out Date dayshiftEndDate, out Time dayshiftEndTime)
        {
            DateTime startDateTime = new DateTime(_date.Year, _date.Month, _date.Day, _dayshiftStartTime.Hour, _dayshiftStartTime.Minute, _dayshiftStartTime.Second);
            DateTime endDateTime = startDateTime.AddMinutes(_shiftMinutes);
            dayshiftEndDate = new Date(endDateTime.Year, endDateTime.Month, endDateTime.Day);
            dayshiftEndTime = new Time(endDateTime.Hour, endDateTime.Minute, endDateTime.Second);
        }

        public void GetNeightshiftStartDateAndTime(out Date neightshiftStartDate, out Time neightshiftStartTime)
        {
            DateTime dayshiftStartDateTime = new DateTime(_date.Year, _date.Month, _date.Day, _dayshiftStartTime.Hour, _dayshiftStartTime.Minute, _dayshiftStartTime.Second);
            DateTime neightshiftStartDateTime = dayshiftStartDateTime.AddMinutes(_shiftMinutes);
            neightshiftStartDate = new Date(neightshiftStartDateTime.Year, neightshiftStartDateTime.Month, neightshiftStartDateTime.Day);
            neightshiftStartTime = new Time(neightshiftStartDateTime.Hour, neightshiftStartDateTime.Minute, neightshiftStartDateTime.Second);
        }

        public void GetNeightshiftEndDateAndTime(out Date neightshiftEndDate, out Time neightshiftEndTime)
        {
            DateTime dayshiftStartDateTime = new DateTime(_date.Year, _date.Month, _date.Day, _dayshiftStartTime.Hour, _dayshiftStartTime.Minute, _dayshiftStartTime.Second);
            DateTime neightshiftEndDateTime = dayshiftStartDateTime.AddMinutes(_shiftMinutes * 2);
            neightshiftEndDate = new Date(neightshiftEndDateTime.Year, neightshiftEndDateTime.Month, neightshiftEndDateTime.Day);
            neightshiftEndTime = new Time(neightshiftEndDateTime.Hour, neightshiftEndDateTime.Minute, neightshiftEndDateTime.Second);
        }

        public int ShiftMinutes
        {
            get { return _shiftMinutes; }
        }

        /// <summary>
        /// 白班的产量。
        /// </summary>
        public int DayshiftCount
        {
            get { return _dayshiftCount; }
        }

        /// <summary>
        /// 夜班的产量。
        /// </summary>
        public int NeightshiftCount
        {
            get { return _neightshiftCount; }
        }

        /// <summary>
        /// 设置白班和夜班的产量。
        /// </summary>
        /// <param name="dayshiftCount"></param>
        /// <param name="neightshiftCount"></param>
        public void SetCount(int dayshiftCount, int neightshiftCount)
        {
            if (dayshiftCount < 0)
                throw new ArgumentOutOfRangeException(nameof(dayshiftCount));

            if (neightshiftCount < 0)
                throw new ArgumentOutOfRangeException(nameof(neightshiftCount));

            _dayshiftCount = dayshiftCount;
            _neightshiftCount = neightshiftCount;
        }
    }
}
