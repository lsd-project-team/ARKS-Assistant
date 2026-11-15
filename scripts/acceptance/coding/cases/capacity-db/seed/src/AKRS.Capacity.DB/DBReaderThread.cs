using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Diagnostics;

namespace AKRS.Capacity.DB
{
	class DBReaderThread : ThreadEx
	{
        Semaphore _semaphore;
        Queue<QueueItemForDBReader> _queue;
        Data _data;

		public DBReaderThread(string dbPath, Semaphore semaphore, Queue<QueueItemForDBReader> queue)
        {
            _semaphore = semaphore;
            _queue = queue;

            _data = new Data(dbPath);
        }

        public override void Dispose()
        {
			base.Dispose();
                       
            if (_data != null)
            {
                _data.Dispose();
                _data = null;
            }
        }


        protected override void Run(object obj)
        {
			Trace.WriteLine("[DBReaderThread::Run()] starts.");

			try
			{
				while (this.Running)
				{
					if (_semaphore.WaitOne(500, false))
					{
						QueueItemForDBReader item;

						lock (_queue)
						{
							item = _queue.Dequeue();
						}

						try
						{
							Record[] recordArray;
							if (item.Records.Length == 1)
								recordArray = _data.GetRecord(item.Records[0]);
							else
								recordArray = _data.GetRecords(item.Records);

							if (recordArray != null)
							{
								item.Records = recordArray;
								item.Succeeded = true;
							}
						}
						catch (Exception e)
						{
							Trace.WriteLine("[DBReaderThread::Run()] {0}.", e.Message);
						}

						if (item.Event != null)
							item.Event.Set();
					}
				}
			}
			catch (Exception e)
			{
				string s = string.Format("[DBReaderThread::Run()] {0}.", e.Message);
				Trace.WriteLine(s);
				Debug.Assert(false, s);
			}
			finally
			{ }

			Trace.WriteLine("[DBReaderThread::Run()] ends.");
        }
	}
}
