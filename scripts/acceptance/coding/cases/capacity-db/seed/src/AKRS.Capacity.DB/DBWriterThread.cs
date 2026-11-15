using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Data.SQLite;
using System.Diagnostics;

namespace AKRS.Capacity.DB
{
    class DBWriterThread : ThreadEx
    {
        Semaphore _semaphore;
        Queue<QueueItemForDBWriter> _queue;

        WaitHandle _capacityEvent;
        CapacityRecord _capacityRecord;

        //WaitHandle _yieldEvent;
        //YieldRecord _yieldRecord;

        Data _data;

        

        public DBWriterThread(string dbPath,
            Semaphore semaphore, Queue<QueueItemForDBWriter> queue,
            WaitHandle capacityEvent, CapacityRecord capacityRecord
            //WaitHandle yieldEvent, YieldRecord yieldRecord
            )
        {
            _semaphore = semaphore;
            _queue = queue;

            _capacityEvent = capacityEvent;
            _capacityRecord = capacityRecord;

            //_yieldEvent = yieldEvent;
            //_yieldRecord = yieldRecord;

            _data = new Data(dbPath);
        }

        public override void Dispose()
        {                     
            if (_data != null)
            {
                _data.Dispose();
                _data = null;
            }
        }


        protected override void Run(object obj)
        {
			Console.WriteLine("[DBWriterThread::Run()] starts.");
			//this.RunImp1(obj);
			this.RunImp2(obj);
			Console.WriteLine("[DBWriterThread::Run()] ends.");
		}

		void RunImp1(object obj)
		{
			Console.WriteLine("[DBWriterThread::RunImp1()] starts.");

			try
			{
				while (true)
				{
					if (_semaphore.WaitOne(500, false))
					{
						QueueItemForDBWriter item;

						lock (_queue)
						{
							item = _queue.Dequeue();
						}

						try
						{
							_data.AddRecord(item.Record);
						}
						catch (Exception e)
						{
							Console.WriteLine("[DBWriterThread::RunImp1()] {0}.", e.Message);
						}

						if (item.Event != null)
							item.Event.Set();
					}
					else
					{
						if (!this.Running)
							break;
					}
				}
			}
			catch (Exception e)
			{
				Console.WriteLine("[DBWriterThread::RunImp1()] {0}.", e.Message);
			}
			finally
			{ }
	
			Console.WriteLine("[DBWriterThread::RunImp1()] ends.");
        }

		void RunImp2(object obj)
		{
			Console.WriteLine("[DBWriterThread::RunImp2()] starts.");

            const int MAX_SIZE = 1000;
			QueueItemForDBWriter[] items = new QueueItemForDBWriter[MAX_SIZE];
            List<Record> recordList = new List<Record>(MAX_SIZE);
			int count = 0;

            //WaitHandle[] waitHandles = new WaitHandle[3];
            WaitHandle[] waitHandles = new WaitHandle[2];
            waitHandles[0] = _semaphore;
            waitHandles[1] = _capacityEvent;
            //waitHandles[2] = _yieldEvent;

            //Stopwatch sw = new Stopwatch();
            //Thread.Sleep(2000);

			try
			{
                while (true)
				{
                    int iRet = WaitHandle.WaitAny(waitHandles, 500, false);
                    //if (iRet != WaitHandle.WaitTimeout)
                    //{
                    //    sw.Reset();
                    //    sw.Start();
                    //}

                    if (iRet == 0)
                    {
                        count = 1;
						while (count < MAX_SIZE && _semaphore.WaitOne(0, false))
							count++;

						lock (_queue)
						{                            
							for (int i = 0; i < count; i++)
                            {
                                QueueItemForDBWriter item = _queue.Dequeue();
								items[i] = item;
                            }
                        }


                        _data.BeginTransaction();
						try
						{
                            for (int i = 0; i < count; i++)
                            {
                                _data.AddRecord(items[i].Record);
                            }
						}
						catch (Exception e)
						{
							Console.WriteLine("[DBWriterThread::Run()] {0}.", e.Message);
						}
						_data.EndTransaction();

                        for (int i = 0; i < count; i++)
						{
							if (items[i].Event != null)
								items[i].Event.Set();
						}
                    }
                    else if (iRet == 1)
                    {
                        count = 1;

                        try
                        {
                            lock (_capacityRecord)
                            {
                                _data.AddRecord(_capacityRecord);
                            }
                        }
                        catch (Exception e)
                        {
                            Console.WriteLine("[DBWriterThread::Run()] {0}.", e.Message);
                        }
                    }
                    //else if (iRet == 2)
                    //{
                    //    count = 1;
                    //    try
                    //    {
                    //        lock (_yieldRecord)
                    //        {
                    //            _data.AddRecord(_yieldRecord);
                    //        }
                    //    }
                    //    catch (Exception e)
                    //    {
                    //        Console.WriteLine("[DBWriterThread::Run()] {0}.", e.Message);
                    //    }
                    //}
                    else
					{
						if (!this.Running)
							break;
					}

                    //if (sw.IsRunning)
                    //{
                    //    sw.Stop();
                    //    Console.WriteLine("count : {0}, {1} ms", count, sw.ElapsedMilliseconds);
                    //}
				}
			}
			catch (Exception e)
			{
				Console.WriteLine("[DBWriterThread::RunImp2()] {0}.", e.Message);
			}
			finally
			{ }
	
			Console.WriteLine("[DBWriterThread::RunImp2()] ends.");
        }


    }
}
