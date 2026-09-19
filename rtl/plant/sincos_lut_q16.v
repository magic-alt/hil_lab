`default_nettype none

module sincos_lut_q16 (
    input  wire [31:0] phase_turn_q32,
    output reg  signed [31:0] sin_q16,
    output reg  signed [31:0] cos_q16
);
    wire [1:0] quadrant;
    wire [5:0] index;
    wire [5:0] reverse_index;
    reg signed [31:0] sin_base;
    reg signed [31:0] cos_base;

    assign quadrant = phase_turn_q32[31:30];
    assign index = phase_turn_q32[29:24];
    assign reverse_index = 6'd63 - index;

    function signed [31:0] sin_lut;
        input [5:0] lut_index;
        begin
            case (lut_index)
            6'd0: sin_lut = 32'sd0;
            6'd1: sin_lut = 32'sd1634;
            6'd2: sin_lut = 32'sd3267;
            6'd3: sin_lut = 32'sd4898;
            6'd4: sin_lut = 32'sd6525;
            6'd5: sin_lut = 32'sd8149;
            6'd6: sin_lut = 32'sd9768;
            6'd7: sin_lut = 32'sd11380;
            6'd8: sin_lut = 32'sd12986;
            6'd9: sin_lut = 32'sd14583;
            6'd10: sin_lut = 32'sd16171;
            6'd11: sin_lut = 32'sd17750;
            6'd12: sin_lut = 32'sd19317;
            6'd13: sin_lut = 32'sd20872;
            6'd14: sin_lut = 32'sd22415;
            6'd15: sin_lut = 32'sd23943;
            6'd16: sin_lut = 32'sd25456;
            6'd17: sin_lut = 32'sd26954;
            6'd18: sin_lut = 32'sd28435;
            6'd19: sin_lut = 32'sd29898;
            6'd20: sin_lut = 32'sd31343;
            6'd21: sin_lut = 32'sd32768;
            6'd22: sin_lut = 32'sd34173;
            6'd23: sin_lut = 32'sd35556;
            6'd24: sin_lut = 32'sd36918;
            6'd25: sin_lut = 32'sd38256;
            6'd26: sin_lut = 32'sd39571;
            6'd27: sin_lut = 32'sd40861;
            6'd28: sin_lut = 32'sd42126;
            6'd29: sin_lut = 32'sd43364;
            6'd30: sin_lut = 32'sd44576;
            6'd31: sin_lut = 32'sd45760;
            6'd32: sin_lut = 32'sd46915;
            6'd33: sin_lut = 32'sd48041;
            6'd34: sin_lut = 32'sd49138;
            6'd35: sin_lut = 32'sd50203;
            6'd36: sin_lut = 32'sd51238;
            6'd37: sin_lut = 32'sd52241;
            6'd38: sin_lut = 32'sd53211;
            6'd39: sin_lut = 32'sd54148;
            6'd40: sin_lut = 32'sd55052;
            6'd41: sin_lut = 32'sd55921;
            6'd42: sin_lut = 32'sd56756;
            6'd43: sin_lut = 32'sd57555;
            6'd44: sin_lut = 32'sd58319;
            6'd45: sin_lut = 32'sd59046;
            6'd46: sin_lut = 32'sd59736;
            6'd47: sin_lut = 32'sd60390;
            6'd48: sin_lut = 32'sd61006;
            6'd49: sin_lut = 32'sd61584;
            6'd50: sin_lut = 32'sd62123;
            6'd51: sin_lut = 32'sd62624;
            6'd52: sin_lut = 32'sd63087;
            6'd53: sin_lut = 32'sd63509;
            6'd54: sin_lut = 32'sd63893;
            6'd55: sin_lut = 32'sd64237;
            6'd56: sin_lut = 32'sd64540;
            6'd57: sin_lut = 32'sd64804;
            6'd58: sin_lut = 32'sd65027;
            6'd59: sin_lut = 32'sd65210;
            6'd60: sin_lut = 32'sd65353;
            6'd61: sin_lut = 32'sd65455;
            6'd62: sin_lut = 32'sd65516;
            6'd63: sin_lut = 32'sd65536;
                default: sin_lut = 32'sd0;
            endcase
        end
    endfunction

    always @* begin
        sin_base = sin_lut(index);
        cos_base = sin_lut(reverse_index);
        case (quadrant)
            2'b00: begin sin_q16 =  sin_base; cos_q16 =  cos_base; end
            2'b01: begin sin_q16 =  cos_base; cos_q16 = -sin_base; end
            2'b10: begin sin_q16 = -sin_base; cos_q16 = -cos_base; end
            default: begin sin_q16 = -cos_base; cos_q16 = sin_base; end
        endcase
    end
endmodule

`default_nettype wire
