`default_nettype none

// Fixed-step averaged PMSM-lite dq plant.
//
// All signed data and coefficients use Q16.16.  Coefficients are discrete-time
// gains and therefore already include the selected model step Ts.
//
//   id[k+1] = id + kvd*vd - krd*id + kcd*(we*iq)
//   iq[k+1] = iq + kvq*vq - krq*iq - kcq*(we*id) - kflux*we
//   Te       = ktorque*iq
//   wm[k+1] = wm + kaccel*(Te-Tload) - kdamp*wm
//   theta[k+1] = theta + ktheta*wm
//
// This intentionally omits saliency torque, inverter switching ripple,
// saturation and friction nonlinearities.  It is the FPGA-Lite single-motor
// plant used before the ZU2CG Full-HIL model.
module pmsm_dq_plant_q16 (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    update_en,

    input  wire signed [31:0]      vd_q16,
    input  wire signed [31:0]      vq_q16,
    input  wire signed [31:0]      load_torque_q16,
    input  wire        [15:0]      pole_pairs,

    input  wire signed [31:0]      k_vd_q16,
    input  wire signed [31:0]      k_vq_q16,
    input  wire signed [31:0]      k_r_d_q16,
    input  wire signed [31:0]      k_r_q_q16,
    input  wire signed [31:0]      k_cross_d_q16,
    input  wire signed [31:0]      k_cross_q_q16,
    input  wire signed [31:0]      k_flux_q16,
    input  wire signed [31:0]      k_torque_q16,
    input  wire signed [31:0]      k_accel_q16,
    input  wire signed [31:0]      k_damp_q16,
    input  wire signed [31:0]      k_theta_q16,

    output reg  signed [31:0]      id_q16,
    output reg  signed [31:0]      iq_q16,
    output reg  signed [31:0]      torque_q16,
    output reg  signed [31:0]      omega_m_q16,
    output reg  signed [31:0]      theta_m_q16,
    output wire signed [31:0]      omega_e_q16
);

    function signed [31:0] qmul;
        input signed [31:0] a;
        input signed [31:0] b;
        reg signed [63:0] product;
        begin
            product = a * b;
            qmul = product >>> 16;
        end
    endfunction

    wire signed [31:0] pole_pairs_q16;
    wire signed [31:0] we_iq_q16;
    wire signed [31:0] we_id_q16;
    wire signed [31:0] torque_next_q16;
    wire signed [31:0] did_q16;
    wire signed [31:0] diq_q16;
    wire signed [31:0] domega_q16;
    wire signed [31:0] dtheta_q16;

    assign pole_pairs_q16 = {pole_pairs, 16'd0};
    assign omega_e_q16 = qmul(omega_m_q16, pole_pairs_q16);
    assign we_iq_q16 = qmul(omega_e_q16, iq_q16);
    assign we_id_q16 = qmul(omega_e_q16, id_q16);

    assign torque_next_q16 = qmul(k_torque_q16, iq_q16);

    assign did_q16 =
        qmul(k_vd_q16, vd_q16) -
        qmul(k_r_d_q16, id_q16) +
        qmul(k_cross_d_q16, we_iq_q16);

    assign diq_q16 =
        qmul(k_vq_q16, vq_q16) -
        qmul(k_r_q_q16, iq_q16) -
        qmul(k_cross_q_q16, we_id_q16) -
        qmul(k_flux_q16, omega_e_q16);

    assign domega_q16 =
        qmul(k_accel_q16, torque_next_q16 - load_torque_q16) -
        qmul(k_damp_q16, omega_m_q16);

    assign dtheta_q16 = qmul(k_theta_q16, omega_m_q16);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            id_q16      <= 32'sd0;
            iq_q16      <= 32'sd0;
            torque_q16  <= 32'sd0;
            omega_m_q16 <= 32'sd0;
            theta_m_q16 <= 32'sd0;
        end else if (update_en) begin
            id_q16      <= id_q16 + did_q16;
            iq_q16      <= iq_q16 + diq_q16;
            torque_q16  <= torque_next_q16;
            omega_m_q16 <= omega_m_q16 + domega_q16;
            theta_m_q16 <= theta_m_q16 + dtheta_q16;
        end
    end

endmodule

`default_nettype wire
