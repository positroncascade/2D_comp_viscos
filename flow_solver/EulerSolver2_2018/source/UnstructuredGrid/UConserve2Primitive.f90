!***********************************/
!	Name:保存変数から基礎変数へ変換するプログラム
!	Alias:UConserve2Primitive
!	Description:定義通りに計算するだけ
!	Type:Geom,CellCenter
!	Input:Geom,CC
!	Output:CC%PrimitiveVariable
!	Note:1~3次元すべてに対応済み
!	Author:Akitaka Toyota
!	Date:2017.11.11
!	Update:2017.11.11
!	Other:
!***********************************/
subroutine UConserve2Primitive(UG,UCC)
    use StructVar_Mod
    use LoopVar_Mod
    use ConstantVar_Mod, Gamma => SpecificOfHeatRatio
    implicit none
    type(UnstructuredGrid), intent(in) :: UG
    type(CellCenter),intent(inout) :: UCC

    iDim = UG%GM%Dimension

!$omp parallel num_threads(CoreNumberOfCPU),shared(UG,UCC,iDim),firstprivate(iCell)
!$omp do
    do iCell=1, UG%GI%AllCells
        UCC%PrimitiveVariable(1,iCell,1,1) = UCC%ConservedQuantity(1,iCell,1,1)

        UCC%PrimitiveVariable(2:iDim+1,iCell,1,1) = &
            &   UCC%ConservedQuantity(2:iDim+1,iCell,1,1)/UCC%ConservedQuantity(1,iCell,1,1)

        UCC%PrimitiveVariable(iDim+2,iCell,1,1) = &
            &   Gmin1 * (UCC%ConservedQuantity(iDim+2,iCell,1,1) - 0.5d0 * UCC%ConservedQuantity(1,iCell,1,1) &
            &   * dot_product(UCC%PrimitiveVariable(2:iDim+1,iCell,1,1),UCC%PrimitiveVariable(2:iDim+1,iCell,1,1)))

    end do
!$omp end do
!$omp end parallel
return
end subroutine UConserve2Primitive
