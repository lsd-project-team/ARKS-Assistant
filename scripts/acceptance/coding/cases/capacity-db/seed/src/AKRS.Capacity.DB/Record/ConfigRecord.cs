using System;
using System.Collections.Generic;
using System.Text;

namespace AKRS.Capacity.DB
{
    class ConfigRecord : Record
    {
        string _strKey;
        string _strVal;

        public ConfigRecord(string strKey, string strVal)
            : base(DateTime.Now)
        {
            if (strKey == null)
                throw new ArgumentNullException(nameof(strKey));

            if (strVal == null)
                throw new ArgumentNullException(nameof(strVal));

            _strKey = strKey;
            _strVal = strVal;
        }

        public ConfigRecord(string strKey)
            : base(DateTime.Now)
        {
            if (strKey == null)
                throw new ArgumentNullException(nameof(strKey));

            _strKey = strKey;
            _strVal = null;
        }

        public void SetValue(string strVal)
        {
            if (strVal == null)
                throw new ArgumentNullException(nameof(strVal));

            _strVal = strVal;
        }

        public string Key
        {
            get { return _strKey; }
        }

        public string Value
        {
            get { return _strVal; }
        }
    }
}
