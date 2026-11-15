using System;
using System.Collections.Generic;
using System.Text;

namespace AKRS.Capacity.DB
{
	struct Classification
	{
		public Classification(int iClass, int iCategory)
		{
			_iClass = iClass;
			_iCategory = iCategory;
		}

		public int Class
		{ get { return _iClass; } }

		public int Category
		{ get { return _iCategory; } }

		int _iClass;
		int _iCategory;
	}
}
