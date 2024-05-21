#ifndef sme_h
#define sme_h

#include <stddef.h>
#include <stdbool.h>

// Return the VL in streaming mode
size_t sme_vector_length(void);

// check feature support
bool supports_hw_feature(const char* name);

// Peak fused multiply-add rate when accumulating to ZA slices
//
//                      | vector group size
//                      -
//      sme_fmla_f32_VGx4_64()
//               ---      --
//  element type  |        | number of ZA slices written
//
// Returned value is the measured date in GFLOPS
//
// SME vector instrutions source the data from 2 or 4 contigous SVE registers, this
// is referred to as the *vector group size*. For example, a VGx4 FMLA multiplies
// four register pairs and accumulates them to four slices of the ZA tile.
//
// On Apple hardware, the SME vector length is 512-bits or 64 bytes, so there are
// 64 ZA slices (ZA[0] .. ZA[63]) of 64 bytes each. We vary the number of slices written
// to determine the minimal number of work required to fully saturate the ALUs. Since the
// entire ZA tile contains 64 slices, we need 16x VGx4 instructions or 32x VGx2 instructions
//

// type: f32, vector group size: 4
double sme_fmla_f32_VGx4_64(void);
double sme_fmla_f32_VGx4_60(void);
double sme_fmla_f32_VGx4_56(void);
double sme_fmla_f32_VGx4_52(void);
double sme_fmla_f32_VGx4_48(void);
double sme_fmla_f32_VGx4_44(void);
double sme_fmla_f32_VGx4_40(void);
double sme_fmla_f32_VGx4_36(void);
double sme_fmla_f32_VGx4_32(void);
double sme_fmla_f32_VGx4_28(void);
double sme_fmla_f32_VGx4_24(void);
double sme_fmla_f32_VGx4_20(void);
double sme_fmla_f32_VGx4_16(void);
double sme_fmla_f32_VGx4_12(void);
double sme_fmla_f32_VGx4_8 (void);
double sme_fmla_f32_VGx4_4 (void);

// type: f32, vector group size: 2
double sme_fmla_f32_VGx2_64(void);
double sme_fmla_f32_VGx2_62(void);
double sme_fmla_f32_VGx2_60(void);
double sme_fmla_f32_VGx2_58(void);
double sme_fmla_f32_VGx2_56(void);
double sme_fmla_f32_VGx2_54(void);
double sme_fmla_f32_VGx2_52(void);
double sme_fmla_f32_VGx2_50(void);
double sme_fmla_f32_VGx2_48(void);
double sme_fmla_f32_VGx2_46(void);
double sme_fmla_f32_VGx2_44(void);
double sme_fmla_f32_VGx2_42(void);
double sme_fmla_f32_VGx2_40(void);
double sme_fmla_f32_VGx2_38(void);
double sme_fmla_f32_VGx2_36(void);
double sme_fmla_f32_VGx2_34(void);
double sme_fmla_f32_VGx2_32(void);
double sme_fmla_f32_VGx2_30(void);
double sme_fmla_f32_VGx2_28(void);
double sme_fmla_f32_VGx2_26(void);
double sme_fmla_f32_VGx2_24(void);
double sme_fmla_f32_VGx2_22(void);
double sme_fmla_f32_VGx2_20(void);
double sme_fmla_f32_VGx2_18(void);
double sme_fmla_f32_VGx2_16(void);
double sme_fmla_f32_VGx2_14(void);
double sme_fmla_f32_VGx2_12(void);
double sme_fmla_f32_VGx2_10(void);
double sme_fmla_f32_VGx2_8 (void);
double sme_fmla_f32_VGx2_6 (void);
double sme_fmla_f32_VGx2_4 (void);
double sme_fmla_f32_VGx2_2 (void);


// type: f64, vector group size: 4
double sme_fmla_f64_VGx4_64(void);
double sme_fmla_f64_VGx4_60(void);
double sme_fmla_f64_VGx4_56(void);
double sme_fmla_f64_VGx4_52(void);
double sme_fmla_f64_VGx4_48(void);
double sme_fmla_f64_VGx4_44(void);
double sme_fmla_f64_VGx4_40(void);
double sme_fmla_f64_VGx4_36(void);
double sme_fmla_f64_VGx4_32(void);
double sme_fmla_f64_VGx4_28(void);
double sme_fmla_f64_VGx4_24(void);
double sme_fmla_f64_VGx4_20(void);
double sme_fmla_f64_VGx4_16(void);
double sme_fmla_f64_VGx4_12(void);
double sme_fmla_f64_VGx4_8 (void);
double sme_fmla_f64_VGx4_4 (void);

// type: f64, vector group size: 2
double sme_fmla_f64_VGx2_64(void);
double sme_fmla_f64_VGx2_62(void);
double sme_fmla_f64_VGx2_60(void);
double sme_fmla_f64_VGx2_58(void);
double sme_fmla_f64_VGx2_56(void);
double sme_fmla_f64_VGx2_54(void);
double sme_fmla_f64_VGx2_52(void);
double sme_fmla_f64_VGx2_50(void);
double sme_fmla_f64_VGx2_48(void);
double sme_fmla_f64_VGx2_46(void);
double sme_fmla_f64_VGx2_44(void);
double sme_fmla_f64_VGx2_42(void);
double sme_fmla_f64_VGx2_40(void);
double sme_fmla_f64_VGx2_38(void);
double sme_fmla_f64_VGx2_36(void);
double sme_fmla_f64_VGx2_34(void);
double sme_fmla_f64_VGx2_32(void);
double sme_fmla_f64_VGx2_30(void);
double sme_fmla_f64_VGx2_28(void);
double sme_fmla_f64_VGx2_26(void);
double sme_fmla_f64_VGx2_24(void);
double sme_fmla_f64_VGx2_22(void);
double sme_fmla_f64_VGx2_20(void);
double sme_fmla_f64_VGx2_18(void);
double sme_fmla_f64_VGx2_16(void);
double sme_fmla_f64_VGx2_14(void);
double sme_fmla_f64_VGx2_12(void);
double sme_fmla_f64_VGx2_10(void);
double sme_fmla_f64_VGx2_8 (void);
double sme_fmla_f64_VGx2_6 (void);
double sme_fmla_f64_VGx2_4 (void);
double sme_fmla_f64_VGx2_2 (void);


// type: fp16->fp32, vector group size: 4
double sme_fmlal_f16f32_VGx4_64(void);
double sme_fmlal_f16f32_VGx4_56(void);
double sme_fmlal_f16f32_VGx4_48(void);
double sme_fmlal_f16f32_VGx4_40(void);
double sme_fmlal_f16f32_VGx4_32(void);
double sme_fmlal_f16f32_VGx4_24(void);
double sme_fmlal_f16f32_VGx4_16(void);
double sme_fmlal_f16f32_VGx4_8 (void);


// type: fp16->fp32, vector group size: 2
double sme_fmlal_f16f32_VGx2_64(void);
double sme_fmlal_f16f32_VGx2_60(void);
double sme_fmlal_f16f32_VGx2_56(void);
double sme_fmlal_f16f32_VGx2_52(void);
double sme_fmlal_f16f32_VGx2_48(void);
double sme_fmlal_f16f32_VGx2_44(void);
double sme_fmlal_f16f32_VGx2_40(void);
double sme_fmlal_f16f32_VGx2_36(void);
double sme_fmlal_f16f32_VGx2_32(void);
double sme_fmlal_f16f32_VGx2_28(void);
double sme_fmlal_f16f32_VGx2_24(void);
double sme_fmlal_f16f32_VGx2_20(void);
double sme_fmlal_f16f32_VGx2_16(void);
double sme_fmlal_f16f32_VGx2_12(void);
double sme_fmlal_f16f32_VGx2_8 (void);
double sme_fmlal_f16f32_VGx2_4 (void);


// Peak outer product accumulating to ZA tiles
//
//                    | number of ZA tiles to write
//                    -
//      sme_fmopa_f32_4()
//                ---
//  element type   |
//
// Returned value is the measured date in GFLOPS
//
// Different operant types imply different number of total ZA tiles. The
// ZA storage is modeled as being a rectangle with a side of VL bits, but due
// to the quadratic nature of data sizes involved, the tile size for each larger
// datatype descreases by a factor of two. That is, a tile of bytes on the 512-bit
// M4 is 64*64 = 4096 bytes, which is the full ZA, but a tile of floats occupies
// only 16*16*4 = 1024 bytes. Thus, there is only 1 byte-element tile, 2 halfword-element
// tiles, 4 word-element tiles, and 8 doubleword-element tiles.
//

// type: fp32->fp32
double sme_fmopa_f32_4(void);
double sme_fmopa_f32_3(void);
double sme_fmopa_f32_2(void);
double sme_fmopa_f32_1(void);

// type: fp64->fp64
double sme_fmopa_f64_8(void);
double sme_fmopa_f64_7(void);
double sme_fmopa_f64_6(void);
double sme_fmopa_f64_5(void);
double sme_fmopa_f64_4(void);
double sme_fmopa_f64_3(void);
double sme_fmopa_f64_2(void);
double sme_fmopa_f64_1(void);

// type: fp16->fp32
double sme_fmopa_f16f32_4(void);
double sme_fmopa_f16f32_3(void);
double sme_fmopa_f16f32_2(void);
double sme_fmopa_f16f32_1(void);

// type: i16->i32
double sme_smopa_i16i32_4(void);
double sme_smopa_i16i32_3(void);
double sme_smopa_i16i32_2(void);
double sme_smopa_i16i32_1(void);

// type: i8->i32
double sme_smopa_i8i32_4(void);
double sme_smopa_i8i32_3(void);
double sme_smopa_i8i32_2(void);
double sme_smopa_i8i32_1(void);


#endif /* sme_h */
