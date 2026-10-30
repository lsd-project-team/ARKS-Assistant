"""Short, useful method locators for the printed appendix."""
import re
from pathlib import Path
PREFERRED={
 'Machine.Operate.cs':['AllAxisGoHome','OpenCompensate','CloseCompensate'],
 'ETelDrive.cs':['Open2DCompensate','DownloadMapping'],
 'GuGaoDrive.cs':['Open2DCompensate','Close2DCompensate'],
 'FrmAdjustDegree.cs':['InitControl','BtDone_Click'],
 'FrmAutoCompensate.cs':['PollTimer_Tick','FinishCollectAndCalculate'],
 'FrmBondCompensate.cs':['BtInput_Click','BtSave_Click'],
 'CompensateCalculator.cs':['Calculate','HuberEstimate'],
 'TransportUnit.cs':['Init','Refresh','GetBondPosition'],
 'BaseMatter.cs':['GetConfigByType','SetMatterDisable'],
 'ProductConfiguration.cs':['GetInstance','Save'],
 'TuService.cs':['CreateMatterCoordinate','UpdateEntity','ReadTransportMapping'],
 'System1Domain.cs':['System1MatterVision','System1MatterMeasureHeight'],
 'System2Domain.cs':['System2MatterVision','System2MatterMeasureHeight'],
 'TUAssistantHelper.cs':['JudgeTuExist','System1MatterVision','System2MatterVision'],
 'UcMainSystem.ShortcutKeys.cs':['UcMainSystem_KeyDown'],
 'TransportController.cs':['TransferDispenseToBond'],
 'BondSubSectionController.cs':['MapBelt'],
 'FrmTransportUnitMapping.cs':['BtRead_Click','BtnRead_Click'],
 'BaseInformation.cs':['IsS1NeedStep','S1FinishedStep'],
 'TransportUnitInfo.cs':[],
 'BondModuleController.cs':['ConvertG0ToMachinePos','GetBondVisionResultPos'],
 'System2Controller.Vision.cs':['GetBondVisionResultPos','UpLookTemperatureCompensationVision'],
 'BondHeadController.cs':['GetNozzleOffset','GetCurrentNozzle'],
 'System2RunTimeProvider.cs':['RecordTime'],
 'SubstrateCameraCorrectionActionNode.Provider.cs':['PrepareBeforeAction','Vision'],
 'SubstrateCameraCorrectionActionNode.MoveHelper.cs':['MoveToIPTVisionPos','MoveToIPTPickPos'],
 'BondActionNode.Provider.cs':['CalculateBondPos'],
 'UcmainSystem.Action.cs':['InitAction'],
 'FrmVisionAlarm.cs':['ManualAlarm','ShowDialog'],
 'Block.cs':['NextDie','ToRequiredAccuracy'],
 'Block.SearchSingle.cs':['SearchSingle'],
 'System2Controller.Assistant.cs':['PlacementTest','UplookVisionAction','CalculatePickPos'],
 'FrmComponentPlacement.cs':['BtnRun_Click','PlacementTest'],
 'TpMarkCompensate.cs':['GetPickCompensation','GetUpLookCompensation'],
 'DefectCompensate.cs':['GetPostBondCompensation','NormalizationOffset'],
}
def method_name(symbol):
 m=re.findall(r'(\w+)\s*\(',symbol)
 return m[-1] if m else '字段定义'
def selected_anchors(f,group=None):
 methods=[a for a in f['anchors'] if '(' in a['symbol'] and ' class ' not in a['symbol'] and '=' not in a['symbol'].split('(')[0] and method_name(a['symbol']) not in ['new','static','字段定义']]
 wanted=PREFERRED.get(Path(f['path']).name,['DoWork','Init','Refresh','SaveInfo','InjectSteps','MapBelt','Save','Read'])
 if Path(f['path']).name=='TuService.cs' and group==14:wanted=['ReadTransportMapping','ReadTransportMappingByComponent']
 found=[]
 for name in wanted:
  match=next((a for a in methods if method_name(a['symbol'])==name),None)
  if match and match not in found:found.append(match)
 if found:return found
 for a in methods:
  if a not in found and method_name(a['symbol']) not in {method_name(x['symbol']) for x in found}:found.append(a)
 return found or [{'line':1,'symbol':'字段定义'}]
