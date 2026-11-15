using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;

namespace AKRS.Capacity.DB
{
    public class QueueItemForDBWriter
    {
        public QueueItemForDBWriter(Record record, ManualResetEvent manualEvent)
        {
            this.Record = record;
            this.Event = manualEvent;
        }


        public Record Record { get; private set; }
        public ManualResetEvent Event { get; private set; }
    }

	public class QueueItemForDBReader
	{
		public QueueItemForDBReader(Record record, ManualResetEvent manualEvent)
        {
			this.Records = new Record[] { record };
            this.Event = manualEvent;

			this.Succeeded = false;
        }

		public QueueItemForDBReader(Record[] records, ManualResetEvent manualEvent)
		{
			// param checking is omitted.

			this.Records = records;
			this.Event = manualEvent;

			this.Succeeded = false;
		}

		public bool Succeeded { get; set; }
        public Record[] Records { get; set; }
        public ManualResetEvent Event { get; private set; }
	}
}
