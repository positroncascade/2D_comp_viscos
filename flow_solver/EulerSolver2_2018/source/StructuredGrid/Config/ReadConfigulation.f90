!***********************************/
!	Name:計算設定を読み込むプログラム
!	Alias:ReadConfigulation
!	Description:専用のCalcConfigファイルが必要
!	Type:Configulation
!	Input:CalcConfig(外部入力)
!	Output:Configulation
!	Note:CalcConfigはプログラム本体と同じディレクトリに置くこと
!	Author:Akitaka Toyota
!	Date:2017.10.26
!	Update:2017.11.07
!	Other:
!***********************************/
subroutine ReadConfigulation(Conf, my_rank)
    use StructVar_Mod
    use ConstantVar_Mod
    implicit none
    type(Configulation), intent(inout) :: Conf
    integer :: my_rank
    character :: cAnnotate
    integer :: tolerance_exp
    logical :: debug = .false.

    call make_logfile_name(Conf%cLogName)

    open(unit=my_rank+100, file='CalcConfig',status='unknown')
        read(my_rank+100,*) cAnnotate
        read(my_rank+100,*) Conf%SwitchProgram, cAnnotate
        read(my_rank+100,*) Conf%UseReadRegion,cAnnotate
        read(my_rank+100,*) Conf%UseResume,cAnnotate
        read(my_rank+100,*) Conf%ResumeFileName
        read(my_rank+100,*) Conf%ResumeFileFormat
        read(my_rank+100,*) Conf%ResumeNumber
        read(my_rank+100,*) Conf%cCaseName
        read(my_rank+100,*) Conf%UseReadBoundaryCond,cAnnotate
        read(my_rank+100,*) Conf%UseVariableTime,cAnnotate
        read(my_rank+100,*) Conf%UseSteadyCalc,cAnnotate
        read(my_rank+100,*) Conf%UseLocalTimeStep,cAnnotate
        read(my_rank+100,*) Conf%UseRRK2,cAnnotate
        read(my_rank+100,*) Conf%UseMUSCL,cAnnotate
        read(my_rank+100,*) Conf%KindLimiter,cAnnotate
        read(my_rank+100,*) Conf%UseOverSet, cAnnotate
        read(my_rank+100,*) FixedTimeStep,cAnnotate
        read(my_rank+100,*) OutputInterval, cAnnotate
        read(my_rank+100,*) IterationNumber,cAnnotate
        read(my_rank+100,*) GridNumber, cAnnotate
        read(my_rank+100,*) SigmoidGain, cAnnotate
        read(my_rank+100,*) EntropyCorrection, cAnnotate
        read(my_rank+100,*) VenkatakrishnanParameterK, cAnnotate
        read(my_rank+100,*) CourantFriedrichsLewyCondition, cAnnotate
        read(my_rank+100,*) Conf%TurbulenceModel, cAnnotate
        read(my_rank+100,*) ReynoldsNumber, cAnnotate
        read(my_rank+100,*) Conf%UseFluxMethod, cAnnotate
        read(my_rank+100,*) Converge_Method
        read(my_rank+100,*) Converge_tolerance, cAnnotate
    close(my_rank+100)

    if(trim(adjustl(Conf%cCaseName)) == "null") Conf%cCaseName = ""
    if(Conf%TurbulenceModel /= 0) invicid = .false.
    if(Conf%UseRRK2 == 1) IterationNumber = 2*IterationNumber
    DefaultTimeStep = FixedTimeStep

    if(Conf%UseJobParallel == 0) then
        Conf%my_rank = 0
    end if

    call Show_Configulation(debug)

    return

contains
    subroutine Show_Configulation(debug)
        logical, intent(in) :: debug

        if (debug == .false.) then
            ! no action
        else
            write(6,*) "show_configulation == TRUE"
            write(6,*) "Conf%SwitchProgram", Conf%SwitchProgram
            write(6,*) "Conf%UseReadRegion", Conf%UseReadRegion
            write(6,*) "Conf%UseResume", Conf%UseResume
            write(6,*) "Conf%ResumeFileName", Conf%ResumeFileName
            write(6,*) "Conf%ResumeFileFormat", Conf%ResumeFileFormat
            write(6,*) "Conf%ResumeNumber", Conf%ResumeNumber
            write(6,*) "Conf%UseReadBoundaryCond", Conf%UseReadBoundaryCond
            write(6,*) "Conf%UseVariableTime", Conf%UseVariableTime
            write(6,*) "Conf%UseSteadyCalc", Conf%UseSteadyCalc
            write(6,*) "Conf%UseLocalTimeStep", Conf%UseLocalTimeStep
            write(6,*) "Conf%UseRRK2", Conf%UseRRK2
            write(6,*) "Conf%UseMUSCL", Conf%UseMUSCL
            write(6,*) "Conf%KindLimiter", Conf%KindLimiter
            write(6,*) "Conf%UseOverSet", Conf%UseOverSet
            write(6,*) "FixedTimeStep", FixedTimeStep
            write(6,*) "OutputInterval", OutputInterval
            write(6,*) "IterationNumber", IterationNumber
            write(6,*) "GridNumber", GridNumber
            write(6,*) "SigmoidGain", SigmoidGain
            write(6,*) "EntropyCorrection", EntropyCorrection
            write(6,*) "VenkatakrishnanParameterK", VenkatakrishnanParameterK
            write(6,*) "CourantFriedrichsLewyCondition", CourantFriedrichsLewyCondition
            write(6,*) "Conf%TurbulenceModel", Conf%TurbulenceModel
            write(6,*) "ReynoldsNumber", ReynoldsNumber
            write(6,*) "UseFluxMethod", Conf%UseFluxMethod
        end if

        return
    end subroutine Show_Configulation

    subroutine make_logfile_name(fname)
        character(len=256), intent(inout) :: fname
        integer :: datetime(8)
        character(len=10) :: sys_time(3)

        call date_and_time(sys_time(1), sys_time(2), sys_time(3), datetime)

        fname = "CalcLog_"//trim(adjustl(sys_time(1)))//"_"//trim(adjustl(sys_time(2)))//".txt"
        return
    end subroutine make_logfile_name

end subroutine ReadConfigulation

