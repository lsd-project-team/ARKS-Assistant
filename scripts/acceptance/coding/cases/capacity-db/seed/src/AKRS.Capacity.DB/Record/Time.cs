using System;
using System.Diagnostics;

namespace AKRS.Capacity.DB
{
    /// <summary>
    /// 24小时制的时间。
    /// </summary>
    public struct Time
    {
        public static int GetMinutes(Time startTime, Time endTime)
        {
            Debug.Assert(startTime.Hour < endTime.Hour);

            DateTime startDateTime = new DateTime(1, 1, 1, startTime.Hour, startTime.Minute, 0);
            DateTime endDateTime = new DateTime(1, 1, 1, endTime.Hour, endTime.Minute, 0);

            TimeSpan timeSpan = endDateTime - startDateTime;
            return (int)timeSpan.TotalMinutes;
        }

        public static bool operator==(Time time1, Time time2)
        {
            return time1._hour == time2._hour && time1._minute == time2._minute && time1._second == time2._second;
        }

        public static bool operator!=(Time time1, Time time2)
        {
            return !(time1 == time2);
        }

        //--------------------------------------------------------------------------------------------------
        //--------------------------------------------------------------------------------------------------

        readonly int _hour;
        readonly int _minute;
        readonly int _second;

        public Time(int hour, int minute, int second)
        {
            if (hour < 0 || hour >= 24)
                throw new ArgumentOutOfRangeException(nameof(hour));

            if (minute < 0 || minute >= 60)
                throw new ArgumentOutOfRangeException(nameof(minute));

            if (second < 0 || second >= 60)
                throw new ArgumentOutOfRangeException(nameof(second));

            _hour = hour;
            _minute = minute;
            _second = second;
        }

        public Time(int hour, int minute)
            : this(hour, minute, 0)
        { }

        public Time(DateTime dateTime)
            : this(dateTime.Hour, dateTime.Millisecond, dateTime.Second)
        { }

        public int Hour { get { return _hour; } }
        public int Minute { get { return _minute; } }
        public int Second { get { return _second; } }

        public override string ToString()
        {
            return String.Format("{0:D2}:{1:D2}:{2:D2}", _hour, _minute, _second);
        }

        public override int GetHashCode()
        {
            return _hour.GetHashCode() ^ _minute.GetHashCode() ^ _second.GetHashCode();
        }

        public override bool Equals(object obj)
        {
            if (obj == null)
            {
                return false;
            }

            try
            {
                Time other = (Time)obj;
                return _hour == other._hour && _minute == other._minute && _second == other._second;
            }
            catch
            {
                return false;
            }
        }

    }
}
