using System;
using System.Collections.Generic;
using System.Text;

namespace AKRS.Capacity.DB
{
	public class CodeNotFoundException : Exception
	{
		public CodeNotFoundException(int iErrorCode)
		{
			this.ErrorCode = iErrorCode;
		}

		public int ErrorCode
		{
			get;
			private set;
		}
	}

    public class IdNotInitializedException : Exception
    {}
}
