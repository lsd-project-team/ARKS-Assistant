using System;
using System.Threading;

namespace AKRS.Capacity.DB
{
	public abstract class ThreadEx : IDisposable
	{
		public ThreadEx()
		{
			_running = false;

			_thread = new Thread(this.Run);
			_thread.IsBackground = true;
		}

		public virtual void Dispose()
		{
			if (_running)
			{
				this.Stop();
				this.Join();
			}
		}

		public ThreadPriority Priority
		{
			get { return _thread.Priority; }
			set { _thread.Priority = value; }
		}


		protected abstract void Run(object obj);

		public virtual void Stop()
		{
			_running = false;
		}

		public virtual void Start()
		{
            this.Start(null);
		}

		public virtual void Start(object obj)
		{
			_running = true;

			_thread.Start(obj);
		}

		public void Join()
		{
			_thread.Join();
		}

		public void Join(int millisecondsTimeout)
		{
			_thread.Join(millisecondsTimeout);
		}

		public void Abort()
		{
			_thread.Abort();
		}

		protected Thread Thread
		{
			get { return _thread; }
		}

		protected bool Running
		{
			get { return _running; }
		}


		private Thread _thread;
		volatile bool _running;
	}
}
