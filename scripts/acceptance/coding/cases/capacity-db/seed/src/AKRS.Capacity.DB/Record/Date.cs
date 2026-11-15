using System;

namespace AKRS.Capacity.DB
{
    /// <summary>
    /// 日期。
    /// </summary>
    public struct Date
    {
        public static explicit operator DateTime(Date date)
        {
            return new DateTime(date.Year, date.Month, date.Day);
        }

        public static bool operator==(Date date1, Date date2)
        {
            return date1._year == date2._year && date1._month == date2._month && date1._day == date2._day;
        }

        public static bool operator!=(Date date1, Date date2)
        {
            return !(date1 == date2);
        }

        readonly int _year;
        readonly int _month;
        readonly int _day;

        /// <summary>
        /// 
        /// </summary>
        /// <param name="year"></param>
        /// <param name="month"></param>
        /// <param name="day"></param>
        public Date(int year, int month, int day)
        {
            if (year <= 0 || year > 9999)
            {
                throw new ArgumentOutOfRangeException(nameof(year));
            }

            if (month <= 0 || month > 12)
            {
                throw new ArgumentOutOfRangeException(nameof(month));
            }

            if (day <= 0 || day > DateTime.DaysInMonth(year, month))
            {
                throw new ArgumentOutOfRangeException(nameof(day));
            }

            _year = year;
            _month = month;
            _day = day;
        }

        public Date(DateTime dateTime)
        {
            _year = dateTime.Year;
            _month = dateTime.Month;
            _day = dateTime.Day;
        }

        public int Year { get { return _year; } }
        public int Month { get { return _month; } }
        public int Day { get { return _day; } }

        public override string ToString()
        {
            return String.Format("{0}-{1:D2}-{2:D2}", _year, _month, _day);
        }

        public override int GetHashCode()
        {
            return _year.GetHashCode() ^ _month.GetHashCode() ^ _day.GetHashCode();
        }

        public override bool Equals(object obj)
        {
            if (obj == null)
                return false;

            try
            {
                Date other = (Date)obj;

                return _year == other._year && _month == other._month && _day == other._day;
            }
            catch
            {
                return false;
            }
        }

        public Date AddDays(int days)
        {
            DateTime dateTime = new DateTime(_year, _month, _day);
            DateTime newDateTime = dateTime.AddDays(days);
            return new Date(newDateTime.Year, newDateTime.Month, newDateTime.Day);
        }


    }
}
