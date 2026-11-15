using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

// 有关程序集的常规信息通过下列属性集
// 控制。更改这些属性值可修改
// 与程序集关联的信息。
[assembly: AssemblyTitle("AKRS.Capacity.DB")]
[assembly: AssemblyDescription("")]
[assembly: AssemblyConfiguration("")]
[assembly: AssemblyProduct("AKRS.Capacity.DB")]
[assembly: AssemblyTrademark("")]
[assembly: AssemblyCulture("")]

// 将 ComVisible 设置为 false 使此程序集中的类型
// 对 COM 组件不可见。如果需要从 COM 访问此程序集中的类型，
// 则将该类型上的 ComVisible 属性设置为 true。
[assembly: ComVisible(false)]

// 如果此项目向 COM 公开，则下列 GUID 用于类型库的 ID
[assembly: Guid("e1af50ec-21b2-4407-a524-d2bac885ca1a")]

// 程序集的版本信息由下面四个值组成:
//
//      主版本
//      次版本 
//      内部版本号
//      修订号
//
// 可以指定所有这些值，也可以使用“内部版本号”和“修订号”的默认值，
// 方法是按如下所示使用“*”:

/*
1.0.0.0
创建。

1.0.1.*
2016-01-07
1.增加了一次调用获得多条记录的功能，仅限于	RecordType.TotalRecord。

1.0.2.*
2016-01-20
1. 对Log表的查询增加了time字段升序。

1.0.3.*
2016-02-02

1.0.4.*
2016-02-03

1.0.5.*
2016-03-11
1. Data.cs增加了RunImp2方法。


1.0.6.*
2016-07-18
1. 增加了一个新类FaultClassification，用于读取并缓存AKRS.Classification.db数据库文件的内容，
	AKRS.Classification.db存储的是与报警分类相关的信息。

1.0.7.*
2017-02-28
1.  （1）LogRecord类增加了
        字段：m_id，
        属性：Id，
        构造函数：
            public LogRecord(int id, DateTime dateTime, STATE state, int code, string info)
   
    （2）Data类增加了
        方法：
            public void RemoveRecord(int id)

    （3）增加了类：
            IdNotInitializedException

1.1.1.*
2017-03-28
（1）Record、CapacityRecord、和YieldRecord类增加了一些方法。
（2）DBWriter和DBWriterThread类的改动：
        对CapacityRecord和YieldRecord对象的写入方法和逻辑进行了更改，
        不再主要依赖于向队列中加入Record的方式。

1.1.2.*
 ThreadEx类给出了Priority属性。
 DBWriter类在创建DBWriterThread对象后，将其的Priority属性设置为ThreadPriority.Highest。

1.2.0.0
2021-05-24
（1）原Capacity表弃用，增加新表cap。
（2）以分钟为单位存一条记录，表示那一分钟的产能。

1.2.1.0
2021-08-10
增加了LogRecord的导出。

1.2.1.1
2021-08-17
Data类增加了InsertOrReplaceRecord方法，该方法使用了SQLite支持的INSERT OR REPLACE语句。
AddRecord(Record)内部不在使用AddRecord(CapacityRecord)和InsertRecord(CapacityRecord)，改为使用InsertOrReplaceRecord方法。

1.2.1.2
2021-12-27
将白班和夜班的工时范围存到数据库中。

1.2.1.3
2021-12-28
修正上个版本中的方法名相似导致的调用错误。

*/

[assembly: AssemblyVersion("1.2.1.3")]
