# 启动、回零与生产放行：源码片段快照

核对日期：2026-10-27。以下片段按现有人工复核依据逐字核对当前 trunk，并保留原文件行号与完整文件 SHA-256。

本快照用于新版阅读样例的固定版本引用；不修改业务源码，也不代表设备运行验收。

## boot-home · Main

原文件：`trunk/AKRS.ZX2200/Program.cs`，L250–256。

文件 SHA-256：`612f00e342d8b9af5bdd6708fdf5b2ca91e9de9495f729f912ff9d2bc0c33c32`。

```csharp
                    if (MachineSoftwareConfiguration.GetInstance().IsAxisResetBeforeWork)
                    {
                        Machine.GetInstance().AllAxisGoHome();
                    }

                    MainForm = new MainForm();
                    Application.Run(MainForm);
```

## form-load-gate · MainForm_Load

原文件：`trunk/AKRS.ZX2200/Main/Controls/MainForm.cs`，L232–271。

文件 SHA-256：`be7edb0cd880cd8258d038ff1278ed89b977aaa8d08a11bc62921b1cc1cd4d39`。

```csharp
        private void MainForm_Load(object sender, EventArgs e)
        {
            if (!Machine.GetInstance().AllAxisReset && !MachineStateModel.GetInstance().IsOffLineWork)
            {
                this.UcMainSystemTile.Enabled = false;
                return;
            }

            SplashScreenManager.ShowForm(typeof(SplashScreen1));
            SplashScreenManager.Default.SendCommand(SplashScreen1.SplashScreenCommand.InitView, "程序加载中");

            // 数据加载
            Machine.GetInstance().DataLoad();

            this.ChangeData();

            // 参数初始化
            UcProgramArgs.InitParamerer = ParameterManage.InitControl;

            // 连接压力表
            ModbusService.GetInstance().ConnectBondhead();
            ModbusService.GetInstance().ConnectManometer();

            Machine.GetInstance().ChoseAllLight();

            Machine.GetInstance().StartBackGroundThread();

            ExportService.EnsureDirectoryExists(@"D:\\设备功能测试");

            try
            {
                MF = (MainForm)Application.OpenForms[0];
            }
            catch (Exception ex) 
            {
                MF = (MainForm)Application.OpenForms[1];
            }

            SplashScreenManager.CloseForm();
        }
```

## home-confirm · AllAxisGoHome

原文件：`trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`，L504–525。

文件 SHA-256：`b45967948d4f5a85c4a2bafceaa0cb01a7cf3e95040cf690fad81df5c187c073`。

```csharp
        public bool AllAxisGoHome()
        {
            try
            {
                if (MachineHardwareConfiguration.GetInstance().IsFlipModuleConfigrated)
                {
                    DialogResult dialog = AKRSXtraMessageBox.Show("回零前请确保焊头和翻转台不干涉！", "提示", MessageBoxButtons.OKCancel, MessageBoxIcon.Information);

                    if (dialog != DialogResult.OK)
                    {
                        return false;
                    }
                }
                else
                {
                    DialogResult dialog = AKRSXtraMessageBox.Show("轴即将复位回零，人员请离开设备", "提示", MessageBoxButtons.OKCancel, MessageBoxIcon.Information);

                    if (dialog != DialogResult.OK)
                    {
                        return false;
                    }
                }
```

## home-prepare · AllAxisGoHome

原文件：`trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`，L527–553。

文件 SHA-256：`b45967948d4f5a85c4a2bafceaa0cb01a7cf3e95040cf690fad81df5c187c073`。

```csharp
                // 收回点胶气缸
                if (MachineHardwareConfiguration.GetInstance().IsSystem2Dispense)
                {
                    System2Domain.GetInstance().S2DispenseController.CloseDispenseHeightMeasurementCylinder();
                }

                LogHelper.Post(Level.Info, $"系统2收回点胶气缸成功", LogCategory.Global, ViewType.InFileAndUI);

                // 设备回零
                this.CloseCompensate();

                LogHelper.Post(Level.Info, $"关闭二维补偿成功", LogCategory.Global, ViewType.InFileAndUI);

                if (MachineHardwareConfiguration.GetInstance().IsEjectSystemConfigured)
                {
                    WaferSubController.GetInstance().MagazineController.ResetWaferPushCylinder();
                    WaferSubController.GetInstance().EjectController.ResetFixedCylinder();
                }

                LogHelper.Post(Level.Info, $"顶针系统初始化成功", LogCategory.Global, ViewType.InFileAndUI);

                if (MachineHardwareConfiguration.GetInstance().IsSlideFluxerConfigured)
                {
                    System2Domain.GetInstance().SlideFluxerController.SlideFluxerHomeNoWait();
                }

                LogHelper.Post(Level.Info, $"静态华夫盒初始化成功", LogCategory.Global, ViewType.InFileAndUI);
```

## home-result · AllAxisGoHome

原文件：`trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`，L555–583。

文件 SHA-256：`b45967948d4f5a85c4a2bafceaa0cb01a7cf3e95040cf690fad81df5c187c073`。

```csharp
                using (DevExpress.Utils.WaitDialogForm sdf = new DevExpress.Utils.WaitDialogForm("轴回零", "轴回零中，请稍后"))
                {
                    LogHelper.Post(Level.Info, $"所有轴开始回零", LogCategory.Global, ViewType.InFileAndUI);
                    bool ret = HardwareRepositoryService.OneKeyHome();
                    LogHelper.Post(Level.Info, $"所有轴完成回零", LogCategory.Global, ViewType.InFileAndUI);
                    if (ret)
                    {
                        //WaferSubController.GetInstance().EjectController.MoveEjectionBankToSlotPosition(0);

                        AKRSXtraMessageBox.Show("所有轴回零成功", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    }
                    else
                    {
                        AKRSXtraMessageBox.Show("轴回零失败", "提示", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        return false;
                    }
                }

                this.OpenCompensate();

                Machine.GetInstance().AllAxisReset = true;

                return true;
            }
            catch (Exception exception)
            {
                AKRSXtraMessageBox.Show(exception.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
```

## ui-start · BarItemStart_ItemClick

原文件：`trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs`，L68–110。

文件 SHA-256：`db4a0051b926beeda4b85fe2905acbf2e630a3bedf47545c3347e1134b19dfe9`。

```csharp
        private void BarItemStart_ItemClick(object sender, ItemClickEventArgs e)
        {
            this.Enabled = false;

            try
            {
                if (MachineSoftwareConfiguration.GetInstance().RecipeWarningBeforeMachineStart)
                {
                    DialogResult dialog = AKRSXtraMessageBox.Show(
                        $"请确认当前程式：{MachineConfigContext.GetInstance().RecipeName} 是否正确?\r\nOK:继续工作\r\nCancel:退出",
                        "提示",
                        MessageBoxButtons.OKCancel,
                        MessageBoxIcon.Question);

                    if (dialog == DialogResult.Cancel)
                    {
                        return;
                    }
                }

                // 开始生产后，关闭方向盘
                DockPanel dockPanel = this.GetDockPanel("ucGuidMove");
                if (dockPanel != null)
                {
                    dockPanel.Close();
                }

                // 退出单步模式
                MachineStateModel.GetInstance().IsSingleStepWork = false;
                this.BarSwitchSingleStep.Checked = false;

                Machine.GetInstance().Start();
            }
            catch (Exception ex)
            {
                Machine.GetInstance().Stop();
                AKRSXtraMessageBox.Show("启动失败" + ex.Message);
            }
            finally
            {
                this.Enabled = true;
            }
        }
```

## prepare-reset · PrepareMachineReadyToStart

原文件：`trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`，L185–196。

文件 SHA-256：`b45967948d4f5a85c4a2bafceaa0cb01a7cf3e95040cf690fad81df5c187c073`。

```csharp
        private bool PrepareMachineReadyToStart()
        {
            this.CleanFile(MachineSoftwareConfiguration.GetInstance().FileSaveDue);

            // 复位信号
            this.ResetMachineSignal();

            // 检测加密狗是否到期
            //if (MachineSoftwareConfiguration.GetInstance().IsDetectingEncryption && !SoftkeyManager.CheckYtSoftKey())
            //{
            //    return false;
            //}
```

## prepare-gates · PrepareMachineReadyToStart

原文件：`trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`，L198–232。

文件 SHA-256：`b45967948d4f5a85c4a2bafceaa0cb01a7cf3e95040cf690fad81df5c187c073`。

```csharp
            // 检查所有是否总复位
            if (!this.AllAxisReset)
            {
                AKRSXtraMessageBox.Show("启动前请先总复位");
                return false;
            }

            this.ReadyToLog();

            if (!this.IsAllowTaskClosed())
            {
                AKRSXtraMessageBox.Show($"部分模组仍在工作,不能启动，请关闭后重试");
                return false;
            }

            foreach (var item in BondProgram.GetInstance().PostBondProgram.PostBondInspections)
            {
                item.InitDefectCount();
            }

            if (!this.MachineInitSuccess())
            {
                return false;
            }

            if (!this.IsSafeDoorClose && MachineHardwareConfiguration.GetInstance().IsSafeDoorConfigured)
            {
                AKRSXtraMessageBox.Show("请先关好安全门");
                return false;
            }

            if (Machine.GetInstance().IsWorking())
            {
                return false;
            }
```

## prepare-motion · PrepareMachineReadyToStart

原文件：`trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`，L234–255。

文件 SHA-256：`b45967948d4f5a85c4a2bafceaa0cb01a7cf3e95040cf690fad81df5c187c073`。

```csharp
            if (MachineHardwareConfiguration.GetInstance().IsSystem1Configrated)
            {
                System1Domain.GetInstance().DispenseController.MoveToSafePos();
            }

            // 轴移动到安全位置,放到流道线程里面
            System2Domain.GetInstance().BondModuleController.MoveToSafePos();

            if (!WaferSubDevicePara.GetInstance().EjectDevicePara.IsShieldEjectModule)
            {
                Axis Axis = HardwareRepositoryService.GetHardware<Axis>("顶针Z");
                Axis.AbsoluteMove(0);
            }


            bool IsSuccess = this.CheckOperatingEnvironment();
            if (IsSuccess == false)
            {
                return false;
            }

            return true;
```

## environment · CheckOperatingEnvironment

原文件：`trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`，L89–128。

文件 SHA-256：`b45967948d4f5a85c4a2bafceaa0cb01a7cf3e95040cf690fad81df5c187c073`。

```csharp
        public bool CheckOperatingEnvironment()
        {
            // 晶圆域有没有准备好
            if (!WaferSystemDomain.GetInstance().CheckIsReady())
            {
                return false;
            }

            // 固晶域启动自检
            if (!System2Domain.GetInstance().CheckIsReady())
            {
                return false;
            }

            // 点胶域有没有准备好
            if (!System1Domain.GetInstance().CheckIsReady())
            {
                return false;
            }

            // 产品有没有准备好
            if (!ProductConfiguration.GetInstance().IsTransportUnitReady())
            {
                return false;
            }

            // 焊点有没有准备好
            if (!ProductConfiguration.GetInstance().BondPositionConfig.IsBpAssistanceFinish())
            {
                return false;
            }

            // 制程是否准备好
            if (!ProcessDomain.GetInstance().CheckIsReady())
            {
                return false;
            }

            return true;
        }
```

## working-state · Start

原文件：`trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`，L261–290。

文件 SHA-256：`b45967948d4f5a85c4a2bafceaa0cb01a7cf3e95040cf690fad81df5c187c073`。

```csharp
        public void Start()
        {
           // Machine.GetInstance().ChoseAllLight();

            // 启动前的检查工作
            bool isSuccess = this.PrepareMachineReadyToStart();
            if (isSuccess == false)
            {
                return;
            }

            Machine.GetInstance().SetState(MachineStateEnum.Working);

            if (!MachineStateModel.GetInstance().IsCompensateWork)
            {
                TransportDomain.GetInstance().StartTask();
                WaferSystemDomain.GetInstance().WaferSubSystemTask.Start();
            }

            if (MachineHardwareConfiguration.GetInstance().IsSystem1Configrated)
            {
                if (!MachineStateModel.GetInstance().IsCompensateWork)
                {
                    System1Domain.GetInstance().DispenseWorkTask.Start();
                }
            }

            // 先排好序
            System2Domain.GetInstance().ActionNodesService.Init();
            System2Domain.GetInstance().BondTask.Start();
```

## start-options · Start

原文件：`trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`，L291–308。

文件 SHA-256：`b45967948d4f5a85c4a2bafceaa0cb01a7cf3e95040cf690fad81df5c187c073`。

```csharp
            if (MachineHardwareConfiguration.GetInstance().IsSlideFluxerConfigured)
            {
                if (!MachineStateModel.GetInstance().IsCompensateWork)
                {
                    System2Domain.GetInstance().SlideFluxerTask.Start();
                }
            }

            if (MachineHardwareConfiguration.GetInstance().IsFlipModuleConfigrated)
            {
                if (!MachineStateModel.GetInstance().IsCompensateWork)
                {
                    WaferSystemDomain.GetInstance().FlipTask.Start();
                }
            }

            WaferSubController.GetInstance().WaferTableController.CheckAndOpenWaffleVacuum();
            WaferSubController.GetInstance().WaferTableController.CheckAndOpenStaticWaffleVacuum();
```

