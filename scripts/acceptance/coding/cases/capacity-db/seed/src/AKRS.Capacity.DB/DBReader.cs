using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Diagnostics;

namespace AKRS.Capacity.DB
{
    public class DBReader : IDisposable
    {
        Queue<QueueItemForDBReader> _queue;
        Semaphore _semaphore;

        DBReaderThread _thread;

        public DBReader(string dbPath)
        {
            _queue = new Queue<QueueItemForDBReader>();
            _semaphore = new Semaphore(0, 1000);

            _thread = new DBReaderThread(dbPath, _semaphore, _queue);
            _thread.Start();
        }


        public void Dispose()
        {
            _thread.Stop();
            _thread.Join();
            _thread = null;

            _queue = null;
            _semaphore = null;
        }


        //public QueueItemForDBReader GetDataAsync(DateTime dateTime, RecordType type)
        //{
        //    Record record = null;
        //    QueueItemForDBReader item = null;

        //    switch (type)
        //    {
        //    case RecordType.CapacityRecord:
        //        record = new CapacityRecordEx(new Date(dateTime), new Time(8, 30), 12 * 60, 0, 0);
        //        break;
        //    case RecordType.LogRecord:
        //        record = new LogRecord(dateTime, 0, 0, null);
        //        break;
        //    }

        //    if (record != null)
        //    {
        //        item = new QueueItemForDBReader(record, new ManualResetEvent(false));

        //        lock (_queue)
        //        {
        //            _queue.Enqueue(item);
        //            _semaphore.Release();
        //        }
        //    }

        //    return item;
        //}

        public bool GetConfigEntrySync(string strKey, out string strVal, int millisecondsTimeout)
        {
            strVal = null;

            if (strKey == null)
                throw new ArgumentNullException(nameof(strKey));

            QueueItemForDBReader item = new QueueItemForDBReader(new ConfigRecord(strKey), new ManualResetEvent(false));

            lock (_queue)
            {
                _queue.Enqueue(item);
                _semaphore.Release();
            }

            item.Event.WaitOne(millisecondsTimeout, false);
            if (item.Succeeded)
            {
                strVal = ((ConfigRecord)item.Records[0]).Value;
            }

            return item.Succeeded;
        }

        public Record[] GetDataSync(DateTime dateTime, RecordType type, int millisecondsTimeout)
        {
            Record[] recordArray = null;
            Record record = null;

            switch (type)
            {
            case RecordType.CapacityRecord:
                //record = new CapacityRecord(dateTime, 0);
                record = new CapacityRecord(new Date(dateTime), new Time(8, 30), 12 * 60);
                break;
            case RecordType.LogRecord:
                record = new LogRecord(dateTime, 0, 0, null);
                break;
                //case RecordType.YieldRecord:
                //	record = new YieldRecord(dateTime, string.Empty, 0);
                //	break;
            }

            Debug.Assert(record != null);

            if (record != null)
            {
                QueueItemForDBReader item = new QueueItemForDBReader(record, new ManualResetEvent(false));

                lock (_queue)
                {
                    _queue.Enqueue(item);
                    _semaphore.Release();
                }

                item.Event.WaitOne(millisecondsTimeout, false);

                if (item.Succeeded)
                    recordArray = (Record[])item.Records.Clone();
            }

            return recordArray;
        }

        public Record[] GetDataSync(DateTime dateTime, RecordType type)
        {
            return this.GetDataSync(dateTime, type, -1);
        }


        public Record[] GetDataSync(DateTime[] dateTimes, RecordType type)
        {
            return this.GetDataSync(dateTimes, type, -1);
        }


        public Record[] GetDataSync(DateTime[] dateTimes, RecordType type, int millisecondsTimeout)
        {
            Record[] recordArray = null;
            Record[] records = null;

            switch (type)
            {
            case RecordType.CapacityRecord:
                //records = new CapacityRecord[dateTimes.Length];
                //for (int i = 0; i < records.Length; i++)
                //	records[i] = new CapacityRecord(dateTimes[i], 0);
                records = new CapacityRecord[dateTimes.Length];
                for (int i = 0; i < records.Length; i++)
                    records[i] = new CapacityRecord(new Date(dateTimes[i]), new Time(8, 30), 12 * 60);
                break;
            case RecordType.LogRecord:
                //record = new DetailRecord(dateTime, 0, 0);
                break;
            }


            if (records != null)
            {
                QueueItemForDBReader item = new QueueItemForDBReader(records, new ManualResetEvent(false));

                lock (_queue)
                {
                    _queue.Enqueue(item);
                    _semaphore.Release();
                }

                item.Event.WaitOne(millisecondsTimeout, false);

                if (item.Succeeded)
                    recordArray = (Record[])item.Records.Clone();
            }

            return recordArray;
        }

        public CapacityRecordEx[] GetDataSync(Date[] dates, Time dayshiftStartTime, Time dayshiftEndTime, Time neightshiftStartTime, Time neightshiftEndTime, int millisecondsTimeout = -1)
        {
            Debug.Assert(dayshiftStartTime.Hour < dayshiftEndTime.Hour);

            int shiftMinutes = Time.GetMinutes(dayshiftStartTime, dayshiftEndTime);

            var records = new CapacityRecordEx[dates.Length];
            for (int i = 0; i < records.Length; i++)
                records[i] = new CapacityRecordEx(dates[i], dayshiftStartTime, shiftMinutes);

            QueueItemForDBReader item = new QueueItemForDBReader(records, new ManualResetEvent(false));

            lock (_queue)
            {
                _queue.Enqueue(item);
                _semaphore.Release();
            }

            item.Event.WaitOne(millisecondsTimeout, false);

            if (item.Succeeded)
            {
                //CapacityRecordEx[] records = new CapacityRecordEx[item.Records.Length];
                //Array.Copy(item.Records, records, records.Length);
                return records;
            }
            else
                return null;
        }

        public Record[] GetLogDataSync(Date firstDate, Date lastDate)
        {
            Record[] recordArray = null;

            var firstDateRecord = new LogRecord((DateTime)firstDate, LogRecord.STATE.Undefined, 0, null);
            var lastDateRecord = new LogRecord((DateTime)lastDate, LogRecord.STATE.Undefined, 0, null);

            var records = new LogRecord[] { firstDateRecord, lastDateRecord };
            QueueItemForDBReader item = new QueueItemForDBReader(records, new ManualResetEvent(false));

            lock (_queue)
            {
                _queue.Enqueue(item);
                _semaphore.Release();
            }

            item.Event.WaitOne(-1, false);

            if (item.Succeeded)
                recordArray = (Record[])item.Records.Clone();

            return recordArray;
        }
    }
}
