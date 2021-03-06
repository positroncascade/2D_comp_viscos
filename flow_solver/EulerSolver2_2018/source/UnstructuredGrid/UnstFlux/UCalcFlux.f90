!***********************************/
!	Name:流束計算プログラムを制御するためのプログラム
!	Alias:CalcFlux
!	Description:
!	Type:CellEdge
!	Input:Configulation,Geometory,CellCenter,CellEdge
!	Output:CE%NormalFluxDiff
!	Note:
!	Author:Akitaka Toyota
!	Date:2017.10.26
!	Update:2017.11.09
!	Other:1次元と2次元,1次精度と2次精度のみに対応
!***********************************/
subroutine UCalcFlux(UConf,UG,UCC,UCE)
    use StructVar_Mod
    use LoopVar_Mod
    implicit none
    type(Configulation), intent(in) :: UConf
    type(UnstructuredGrid), intent(in) :: UG
    type(CellCenter), intent(inout) :: UCC
    type(CellEdge), intent(inout) :: UCE

    interface
        subroutine UUpwindFlux_Dim2(UG,UCE,UCC) !MUSCL経由の場合CEのみ，1次精度の場合CCを渡す
            use StructVar_Mod
            type(UnstructuredGrid), intent(in) :: UG
            type(CellEdge), intent(inout) :: UCE
            type(CellCenter), intent(in), optional :: UCC
        end subroutine UUpwindFlux_Dim2
    end interface

    interface
        subroutine JPUUpwindFlux_Dim2(UG,UCE,UCC) !MUSCL経由の場合CEのみ，1次精度の場合CCを渡す
            use StructVar_Mod
            type(UnstructuredGrid), intent(in) :: UG
            type(CellEdge), intent(inout) :: UCE
            type(CellCenter), intent(in), optional :: UCC
        end subroutine JPUUpwindFlux_Dim2
    end interface


    if(UConf%UseJobParallel == 1) then
        call JPUCalcFlux(UConf, UG, UCC, UCE)
    else
        if(UConf%UseMUSCL == 1) then
            call UMUSCL(UConf,UG,UCC,UCE)
        end if


        if(UConf%UseMUSCL == 0) then
            call UUpwindFlux_Dim2(UG,UCE,UCC)

        else if(UConf%UseMUSCL == 1) then
            if(UConf%UseFluxMethod == 0) then
                call UUpwindFlux_Dim2(UG,UCE)
            else if (UConf%UseFluxMethod == 1) then
                call USlau2(UConf, UG, UCC, UCE)
            end if
        end if

        if(UConf%TurbulenceModel == 1) then
            call URansCommon(UConf, UG, UCC, UCE)
        end if
    end if

    return
contains

    subroutine JPUCalcFlux(UConf,UG,UCC,UCE)
    implicit none
        type(Configulation), intent(in) :: UConf
        type(UnstructuredGrid), intent(in) :: UG
        type(CellCenter), intent(inout) :: UCC
        type(CellEdge), intent(inout) :: UCE

        if(UConf%UseMUSCL == 1) then
            call JPUMUSCL(UConf, UG, UCC, UCE)
        else
            call JPUConserve2Primitive(UG, UCC)
        end if

        if(UConf%UseFluxMethod == 0) then
            call JPUUpwindFlux_Dim2(UG,UCE,UCC)
        else
            call USlau2(UConf, UG, UCC, UCE)
        end if

        if(UConf%TurbulenceModel == 1) then
            call URansCommon(UConf, UG, UCC, UCE)
        end if

        return
    end subroutine JPUCalcFlux

end subroutine UCalcFlux
