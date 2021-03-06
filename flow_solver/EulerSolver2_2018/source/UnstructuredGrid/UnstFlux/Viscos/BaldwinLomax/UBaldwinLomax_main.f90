!***********************************/
!	Name:粘性流束を計算するためのプログラム
!	Alias:UBaldwinLomax_main
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
subroutine UBaldwinLomax_main(UConf, UG, UCC, UCE)
    use StructVar_Mod
    use LoopVar_Mod
    use ConstantVar_Mod, gamma => SpecificOfHeatRatio, KC => KarmanConstant
    use FrequentOperation
    implicit none
    type(Configulation), intent(in) :: UConf
    type(UnstructuredGrid), intent(in) :: UG
    type(CellCenter), intent(inout) :: UCC
    type(CellEdge), intent(inout) :: UCE
    integer :: iWall, iMember    ! for Loop

    double precision :: Wall_Density, Wall_Viscosity, Wall_dudy ! dudy is vertical direction gradient of tangential velocity on wall
    double precision :: yMax, Fmax, Udif, Fwake
    double precision, parameter :: Cwk = 0.25d0
    integer :: iY_max_num!, y_max_num(:)    ! y_maxを与えるCellNum(壁ごとの局所番号)
    double precision, allocatable :: mixing_length(:)   ! iWallごとmixing_length

! Baldwin-Lomax
!$omp parallel num_threads(CoreNumberOfCPU), default(private), shared(UConf, UG, UCC, UCE), firstprivate(iWall, iMember)
!$omp do
    ! loop of wall
    do iWall=1, UG%GM%BC%iWallTotal
        ! get density, viscosity, and velocity gradient on wall
        call GetWallVariable(UG, UCC, UCE, iWall, Wall_Density, Wall_Viscosity, Wall_dudy)

        allocate(mixing_length(UG%GM%BC%VW(iWall)%iNumberOfMemberEdge))
        ! get y_plus & mixing_length
        do iMember = 1, UG%GM%BC%VW(iWall)%iNumberOfMemberEdge
            mixing_length(iMember) = set_mixing_length(Wall_Density, Wall_Viscosity, Wall_dudy, UG%Line%Distance(UG%GM%BC%VW(iWall)%iMemberEdge(iMember)))
        end do

        ! get y_max, F_max, and u_dif on each wall boundary respectively
        call CalcYmaxAndFmax_Udif(UCE%RebuildQunatity, mixing_length, UCE%AbsoluteVortisity(:, 1, 1), UG%GM%BC%VW(iWall), iY_max_num, Fmax, Udif)
        ! 壁番号→壁に所属する要素の総数，近い順に整列済みでセル番号の検索が可能，高速巡回が可能なように内部では配列にしておく

        yMax = UG%Line%Distance(UG%GM%BC%VW(iWall)%iMemberEdge(iY_max_num))

        UCC%debug(UG%Line%Cell(UG%GM%BC%VW(iWall)%iGlobalEdge, 1, 1), 1) = yMax    ! debug

        if(Fmax == 0.0d0) then
            Fwake = 0.0d0
        else
            Fwake = min(yMax * Fmax, Cwk * yMax * (Udif ** 2) / Fmax)
        end if

        ! Calc Turbulance Viscosity of Baldwin-Lomax Model
        call GetEddyViscosity(UG%GM%BC%VW(iWall), mixing_length**2, Fwake, yMax, UG%Line%Distance(:), UCE)
        deallocate(mixing_length)
    end do


!$omp end do
!$omp end parallel
    return
contains

    function set_y_plus(rho_w, mu_w, dudy_w, y) result(y_plus)
        implicit none
        double precision, intent(in) :: rho_w, mu_w, dudy_w, y   ! 壁表面での密度，せん断応力，粘性係数，壁からの垂直距離
        double precision :: y_plus

        y_plus = sqrt(rho_w / mu_w * dudy_w) * y ! 定義確認!

        return
    end function set_y_plus


    function set_mixing_length(rho_w, mu_w, dudy_w, y) result (l_mix)
        implicit none
        double precision, intent(in) :: rho_w, dudy_w, mu_w, y   ! 壁表面での密度，せん断応力，粘性係数，壁からの垂直距離
        double precision :: l_mix
        double precision :: A_plus = 26.0d0

        l_mix = KC * y * (1.0d0 - exp(-set_y_plus(rho_w, mu_w, dudy_w, y) / A_plus))

        return
    end function set_mixing_length


    subroutine CalcYmaxAndFmax_Udif(RQ, l_mix, Vortisity, VW, iYmax_id, Fmax, Udif)
        implicit none
        double precision, intent(in) :: RQ(:, :, :, :, :), l_mix(:), Vortisity(:)   ! RQ:大域界面番号，l_mix:壁内局所界面番号，Vortisity:大域界面番号
        type(ViscosityWall), intent(in) :: VW   ! iWall固定済み
        double precision, intent(out) :: Fmax, Udif ! Baldwin(1978)のeq.8
        integer, intent(out) :: iYmax_id    ! 壁内局所界面番号
        double precision :: tmpF, tmpU, tmpUmax, tmpUmin
        integer :: iMem, iEdgeNum   ! 壁内局所界面番号，大域界面番号

        Fmax = 0.0d0
        tmpUmax = 0.0d0
        tmpUmin = 100000000.0d0

        iYmax_id = 1
        do iMem = 1, VW%iNumberOfMemberEdge
            iEdgeNum = VW%iMemberEdge(iMem) ! iWallに属するiMem番目の界面について
            tmpF = Vortisity(iEdgeNum) * l_mix(iMem) / KC   !
            tmpU = 0.5d0 * (AbsVector(RQ(2:4, 1, 1, 1, iEdgeNum)) + AbsVector(RQ(2:4, 1, 1, 2, iEdgeNum)))  ! 界面裏表速度の単純平均値にしている(高マッハ数で不安定になるかも)

            if(tmpF > Fmax) then
                Fmax = tmpF
                iYmax_id = iMem
            end if

            tmpUmax = max(tmpU, tmpUmax)
            tmpUmin = min(tmpU, tmpUmin)
        end do

        Udif = tmpUmax - tmpUmin

        return
    end subroutine CalcYmaxAndFmax_Udif


    subroutine GetEddyViscosity(VW, l_mix2, Fwake, yMax, Distance, UCE)
        implicit none
        type(ViscosityWall), intent(in) :: VW
        double precision, intent(in) :: Distance(:)   ! 大域セル番号で検索
        double precision, intent(in) :: l_mix2(:), Fwake, yMax  ! 局所セル番号で検索
        type(CellEdge), intent(inout) :: UCE

        double precision, parameter :: Ccp = 1.6d0, Ckleb = 0.3d0
        integer :: iMem, iFlag, iEdgeNum
        double precision :: Fkleb, Mu_in, Mu_out, rho_wall, Mu_max, Mu_t

        !iFlag = 1
        do iMem = 1, VW%iNumberOfMemberEdge
            iEdgeNum = VW%iMemberEdge(iMem)
            if(yMax == 0.0d0) then
                Fkleb = 0.0d0
            else
                Fkleb = 1.0d0 / (1.0d0 + 5.5d0 * (Ckleb * Distance(iEdgeNum) / yMax) ** 6)
            end if

            rho_wall = 0.5d0 * (UCE%RebuildQunatity(1, 1, 1, 2, iEdgeNum) + UCE%RebuildQunatity(1, 1, 1, 1, iEdgeNum))  ! 密度は壁両側の算術平均
            Mu_out = ClauserConstant * Ccp * rho_wall * Fwake * Fkleb


            Mu_in = rho_wall * l_mix2(iMem) * UCE%AbsoluteVortisity(iEdgeNum, 1, 1)
            Mu_max = max(Mu_in, Mu_out)
            Mu_t = min(Mu_in, Mu_out)

            if (Mu_max > C_mutm * UCE%LaminarViscosity(iEdgeNum,1,1)) then
                UCE%EddyViscosity(iEdgeNum, 1, 1) = Mu_t
            else
                UCE%EddyViscosity(iEdgeNum, 1, 1) = 0.0d0
            end if

        end do

        return
    end subroutine GetEddyViscosity

end subroutine UBaldwinLomax_main
