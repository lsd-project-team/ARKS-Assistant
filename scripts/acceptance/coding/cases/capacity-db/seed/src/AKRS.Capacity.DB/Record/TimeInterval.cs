using System;
using System.Collections.Generic;
using System.Text;

namespace AKRS.Capacity.DB
{
	/// <summary>
	/// 时间区间。用于表示从HH:MM:SS到hh:mm:ss的时间区间。
	/// </summary>
	public struct ShiftTimeInterval : IEquatable<ShiftTimeInterval>
	{
        public static bool operator==(ShiftTimeInterval operand1, ShiftTimeInterval operand2)
        {
            return operand1.Equals(operand2);
        }

        public static bool operator!=(ShiftTimeInterval operand1, ShiftTimeInterval operand2)
        {
            return !operand1.Equals(operand2);
        }



		readonly int _startTimeHour;
		readonly int _startTimeMinute;
		readonly int _startTimeSecond;

		readonly int _endTimeHour;
		readonly int _endTimeMinute;
		readonly int _endTimeSecond;

		readonly bool _bSameDay;



		/// <summary>
		/// 
		/// </summary>
		/// <param name="startTimeHour">0~23</param>
		/// <param name="endTimeHour">0~60</param>
		/// <exception cref="ArgumentOutOfRangeException">参数超出有效返回。</exception>
		public ShiftTimeInterval(int startTimeHour, int endTimeHour)
			: this(startTimeHour, 0, 0, endTimeHour, 0, 0)
		{
		}

		/// <summary>
		/// 
		/// </summary>
		/// <param name="startTimeHour">0~23</param>
		/// <param name="startTimeMiniute">0~60</param>
		/// <param name="startTimeSecond">0~60</param>
		/// <param name="endTimeHour">0~23</param>
		/// <param name="endTimeMinute">0~60</param>
		/// <param name="endTimeSecond">0~60</param>
		/// <exception cref="ArgumentOutOfRangeException">参数超出有效返回。</exception>
		public ShiftTimeInterval(
			int startTimeHour, int startTimeMiniute, int startTimeSecond,
			int endTimeHour, int endTimeMinute, int endTimeSecond
			)
		{
			if (startTimeHour < 0 || startTimeHour > 23)
				throw new ArgumentOutOfRangeException("startTimeHour");

			if (startTimeMiniute < 0 || startTimeMiniute > 60)
				throw new ArgumentOutOfRangeException("startTimeMinute");

			if (startTimeSecond < 0 || startTimeSecond > 60)
				throw new ArgumentOutOfRangeException("startTimeSecond");

			if (endTimeHour < 0 || endTimeHour > 23)
				throw new ArgumentOutOfRangeException("endTimeHour");

			if (endTimeMinute < 0 || endTimeMinute > 60)
				throw new ArgumentOutOfRangeException("endTimeMinute");

			if (endTimeSecond < 0 || endTimeSecond > 60)
				throw new ArgumentOutOfRangeException("endTimeSecond");


			_startTimeHour = startTimeHour;
			_startTimeMinute = startTimeMiniute;
			_startTimeSecond = startTimeSecond;
			_endTimeHour = endTimeHour;
			_endTimeMinute = endTimeMinute;
			_endTimeSecond = endTimeSecond;

			_bSameDay = true;

			if (_endTimeHour < _startTimeHour)
			{
				_bSameDay = false;
			}
		}

		public int StartTimeHour
		{
			get { return _startTimeHour; }
		}

		public int StartTimeMinute
		{
			get { return _startTimeMinute; }
		}

		public int StartTimeSecond
		{
			get { return _startTimeSecond; }
		}
		
		public int EndTimeHour
		{
			get { return _endTimeHour; }
		}

		public int EndTimeMinute
		{
			get { return _endTimeMinute; }
		}

		public int EndTimeSecond
		{
			get { return _endTimeSecond; }
		}

		public bool SameDay
		{
			get { return _bSameDay; }
		}

        public override int GetHashCode()
        {
            return
                _startTimeHour.GetHashCode() ^ _startTimeMinute.GetHashCode() ^ _startTimeSecond.GetHashCode()
                ^
                _endTimeHour.GetHashCode() ^ _endTimeMinute.GetHashCode() ^ _endTimeSecond.GetHashCode();
        }

        public override bool Equals(object obj)
        {
            try
            {
                return Equals((ShiftTimeInterval)obj);
            }
            catch
            {
                return false;
            }
        }

        public bool Equals(ShiftTimeInterval other)
        {
            return _startTimeHour == other._startTimeHour &&
                   _startTimeMinute == other._startTimeMinute &&
                   _startTimeSecond == other._startTimeSecond &&
                   _endTimeHour == other._endTimeHour &&
                   _endTimeMinute == other._endTimeMinute &&
                   _endTimeSecond == other._endTimeSecond;
        }

        public override string ToString()
        {
            return String.Format("{0,2:D2}:{1,2:D2}:{2,2:D2} ~ {3,2:D2}:{4,2:D2}:{5,2:D2}",
                _startTimeHour, _startTimeMinute, _startTimeSecond, _endTimeHour, _endTimeMinute, _endTimeSecond);
        }
    }
}
