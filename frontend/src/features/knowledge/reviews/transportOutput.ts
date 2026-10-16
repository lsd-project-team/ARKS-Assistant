import { flow, outcome, step } from './builders.ts';

export const transportOutputFlows = [
  flow(
    'transport-belt-unload',
    '等待区进入出料皮带',
    'None 在出料任务分配前返回；其他非 LoaderBin 配置创建等待区到出料皮带任务。控制器同时检查物料检测与记忆。',
    ['tr-output-task', 'tr-out-gate'],
    [
      step(
        'gate',
        '检查等待区与出口占用',
        '等待区传感器未检测到物料或记忆为 NoMaterial 均返回 NoStart。Online、OnlineWithAutoUnloader 还检查出料段物料传感器；仅 Online 再检查出料段 Transfering 或 HasMaterial。',
        ['tr-out-gate'],
      ),
      step(
        'wait',
        '等待段启动与入口检测',
        'retry 先置等待区 Transfering 并启动皮带，运动时检测出料控制器入口。未检测到时报警，Retry 回 retry，Abort 返回，Ignore 跳过出料段运动的 else 并进入共同提交。',
        ['tr-out-first', 'tr-out-commit'],
      ),
      step(
        'out',
        '出料皮带运行与卡料复查',
        '检测到入口物料后启动出料皮带；入口变为无料时停止等待段，是否停止出料皮带受连续运动配置影响。之后报警条件实际比较“入口仍有料或等待区仍有料”；读取的出料段 HasMaterialInModule 结果未用于该 if。',
        ['tr-out-second'],
        [
          outcome(
            '局部重试',
            '报警 Retry 回等待段启动处 retry，Abort 返回，Ignore 继续提交。代码旁的 H 传感器注释不能代替实际 if 的两个变量。',
            'tr-out-second',
          ),
        ],
      ),
      step(
        'commit',
        '更新出料段载具与状态',
        '等待区载具交给出料段并 Refresh，清等待区载具与物料，出料段置 HasMaterial，两段 Ready，保存后返回 Success。catch 只恢复进入方法时保存的等待区物料状态，返回 Exception。',
        ['tr-out-commit'],
        [
          outcome(
            '线程结果',
            'Abort、Exception 调用 Stop，NoStart、Success 进入下一轮；该段未在 Success 发布单独的完成信号。',
            'tr-output-task',
          ),
        ],
      ),
    ],
  ),
  flow(
    'transport-bin-unload',
    '等待区进入下料仓',
    'LoaderBin 线程先等待 UnloaderAllowPushSignal，才调用下料控制器；成功后控制器推进层号，线程再发允许料仓移动。',
    ['tr-output-bin', 'tr-unload-commit'],
    [
      step(
        'gate',
        '检查许可与等待区',
        '允许推料 Wait=false 退出线程。控制器在等待区检测无料、记忆无料或等待皮带仍运动时返回 NoStart；线程延时后 continue，不复位许可、不请求换层。',
        ['tr-output-bin', 'tr-unload-gate'],
      ),
      step(
        'belt',
        '先运行等待段',
        'retry 启动等待段皮带；运动时检测等待区物料，变为无料时退出检测循环。若运动结束仍有料则报警：Retry 回 retry，Abort 返回，Ignore 跳过推杆分支继续共同提交。',
        ['tr-unload-belt', 'tr-unload-commit'],
      ),
      step(
        'push',
        '推入料仓与重试',
        '正常进入 RePush 时先回推杆再 PushTabletToUnloader，以后一次返回值判断。推料非 Success 时 Retry 回 RePush；推后等待区仍有料时 Retry 先回推杆，再回 retry 重新运行皮带。两处 Abort 返回，Ignore 继续。',
        ['tr-unload-push'],
      ),
      step(
        'commit',
        '推进层号并交还许可',
        '末尾回推杆、停止等待段，清等待区载具并置无料，出料段置有料、两段 Ready，AddCurPlaceLayer 加一后保存并返回 Success。线程等 200 毫秒、复位推料许可、发 AllowUnloaderMoveSignal。',
        ['tr-unload-commit', 'tr-unloader-inc', 'tr-output-bin'],
        [
          outcome(
            'Abort / Exception',
            '线程调用 Stop 并 return，不执行后续许可复位和允许移动。控制器 catch 只恢复等待区物料状态，并返回 Exception。',
            'tr-output-bin',
            'tr-unload-commit',
          ),
          outcome(
            '忽略报警',
            '上述 Ignore 路径仍可能清物料、加层号并返回 Success，不能写成这些分支都已确认实物入仓。',
            'tr-unload-belt',
            'tr-unload-push',
            'tr-unload-commit',
          ),
        ],
      ),
    ],
  ),
  flow(
    'transport-online-unload',
    '出料皮带交给收板机',
    'Online 或 OnlineWithAutoUnloader 创建此线程。出料段记忆与收板机要料信号满足后才启动交接。',
    ['tr-output-online', 'tr-online-out'],
    [
      step(
        'gate',
        '检查物料与外部要料',
        '出料段记忆无料、传输状态为 Transfering 或未收到 GetAutoUnLoaderNeedMaterialSignal，都返回 NoStart。',
        ['tr-online-out'],
      ),
      step(
        'transfer',
        '检查出口出现与离开',
        'retry 启动出料皮带，先等出口检测到物料，再检测出口变无料，延时 500 毫秒后停止皮带。两次卡料报警都可 Retry 回皮带启动处、Abort 返回、Ignore 继续提交。',
        ['tr-online-out'],
      ),
      step(
        'finish',
        '清出料段状态',
        '清 TransportUnit，置 NoMaterial 与 Ready，保存后返回 Success。线程在 NoStart 延时、Abort 调用 Stop，Success 继续循环；该 switch 没有 Exception 分支，catch 只显示异常。',
        ['tr-online-out', 'tr-output-online'],
      ),
    ],
  ),
];
