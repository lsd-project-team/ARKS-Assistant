using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;

namespace AKRS.Capacity.DB
{
    public class DBWriter : IDisposable
    {
        Queue<QueueItemForDBWriter> _queue;
        Semaphore _semaphore;

        CapacityRecord _lastCapacityRecord;
        AutoResetEvent _capacityEvent;

        //YieldRecord _lastYieldRecord;
        //AutoResetEvent _yieldEvent;
        

        DBWriterThread _dataThread;
        

        public DBWriter(string dbPath)
        {
            _queue = new Queue<QueueItemForDBWriter>();
            _semaphore = new Semaphore(0, 1000);

            _lastCapacityRecord = new CapacityRecord(new Date(1, 1, 1), new Time(0, 0), 0);
            _capacityEvent = new AutoResetEvent(false);

            //_lastYieldRecord = new YieldRecord(new DateTime(), String.Empty, 0);
            //_yieldEvent = new AutoResetEvent(false);            

            //_dataThread = new DBWriterThread(dbPath, _semaphore, _queue, _capacityEvent, _lastCapacityRecord, _yieldEvent, _lastYieldRecord);
            _dataThread = new DBWriterThread(dbPath, _semaphore, _queue, _capacityEvent, _lastCapacityRecord);
            _dataThread.Priority = ThreadPriority.Highest;
            _dataThread.Start();
        }

        
        public void Dispose()
        {
            _dataThread.Stop();
            _dataThread.Join();
            _dataThread = null;

            _queue = null;
            _semaphore = null;

            _lastCapacityRecord = null;
            //_lastYieldRecord = null;
            _capacityEvent = null;
        }


        // insert record into the Capacity table.
        //
        public void AddData(DateTime dateTime, int count, ManualResetEvent manualEvent)
        {
            CapacityRecord record = new CapacityRecord(new Date(dateTime), new Time(dateTime), count);
            QueueItemForDBWriter item = new QueueItemForDBWriter(record, manualEvent);

            lock (_queue)
            {
                _queue.Enqueue(item);
            }

            _semaphore.Release();
        }


        public void AddData(DateTime dateTime, int count)
        {
            Date date = new Date(dateTime);
            Time time = new Time(dateTime.Hour, dateTime.Minute);
            AddData(date, time, count);
        }

        public void AddData(Date date, Time time, int count)
        {
            if (_lastCapacityRecord.Date != date && _lastCapacityRecord.Time != time)
            {
                CapacityRecord copy = new CapacityRecord(_lastCapacityRecord);

                lock (_queue)
                {
                    _queue.Enqueue(new QueueItemForDBWriter(copy, null));
                }

                _semaphore.Release();
            }

            lock (_lastCapacityRecord)
            {
                _lastCapacityRecord.Set(date, time, count);
            }

            _capacityEvent.Set();
        }


        //// insert record into a Log table.
        ////
        public void AddData(DateTime dateTime, LogRecord.STATE state, int errorCode, string info, ManualResetEvent manualEvent)
        {
            LogRecord record = new LogRecord(dateTime, state, errorCode, info);
            QueueItemForDBWriter item = new QueueItemForDBWriter(record, manualEvent);

            lock (_queue)
            {
                _queue.Enqueue(item);
            }

            _semaphore.Release();
        }

        //// insert record into a Log table.
        ////
        public void AddData(DateTime dateTime, LogRecord.STATE state, int errorCode, string info)
        {
            this.AddData(dateTime, state, errorCode, info, null);
        }


		//// insert record into the Yield table.
		////
        //public void AddData(DateTime dateTime, string id, int count, ManualResetEvent manualEvent)
        //{
        //    YieldRecord record = new YieldRecord(dateTime, id, count);
        //    QueueItemForDBWriter item = new QueueItemForDBWriter(record, manualEvent);

        //    lock (_queue)
        //    {
        //        _queue.Enqueue(item);
        //    }

        //    //try
        //    //{
        //        _semaphore.Release();
        //    //}
        //    //catch (SemaphoreFullException e)
        //    //{
        //        //Console.WriteLine(e.Message);
        //    //}
        //}


        //public void AddData(DateTime dateTime, string id, int count)
        //{
        //    this.AddData(dateTime, id, count, null);
        //}

        //public void AddData(DateTime dateTime, string id, int count)
        //{
        //    if (_lastYieldRecord.DateTime != dateTime || _lastYieldRecord.Id != id)
        //    {
        //        YieldRecord copy = new YieldRecord(_lastYieldRecord);
             
        //        lock (_queue)
        //        {
        //            _queue.Enqueue(new QueueItemForDBWriter(copy, null));
        //        }

        //        _semaphore.Release();
        //    }
            
        //    lock (_lastYieldRecord)
        //    {
        //        _lastYieldRecord.Set(dateTime, id, count);
        //    }

        //    _yieldEvent.Set();
        //}

        public void SetData(string strKey, string strValue)
        {
            if (strKey == null)
                throw new ArgumentNullException(nameof(strKey));

            if (strValue == null)
                throw new ArgumentNullException(nameof(strValue));

            {
                ConfigRecord configRecord = new ConfigRecord(strKey, strValue);

                lock (_queue)
                {
                    _queue.Enqueue(new QueueItemForDBWriter(configRecord, null));
                }

                _semaphore.Release();
            }
        }
    }
}
