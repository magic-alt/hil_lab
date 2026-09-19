`default_nettype none

module abz_encoder_emulator #(
    parameter COUNTS_PER_REV = 4096
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    input  wire        direction_forward,
    input  wire [31:0] step_period_ticks,

    output reg         enc_a,
    output reg         enc_b,
    output reg         enc_z,
    output reg  [31:0] position_edges
);

    reg [31:0] tick_count;
    reg [31:0] revolution_edge_count;
    reg [1:0]  phase;
    reg [1:0]  next_phase;

    wire step_due;

    assign step_due = (step_period_ticks <= 32'd1) ?
                      1'b1 :
                      (tick_count >= (step_period_ticks - 32'd1));

    always @* begin
        next_phase = phase;
        if (direction_forward) begin
            case (phase)
                2'b00: next_phase = 2'b01;
                2'b01: next_phase = 2'b11;
                2'b11: next_phase = 2'b10;
                2'b10: next_phase = 2'b00;
                default: next_phase = 2'b00;
            endcase
        end else begin
            case (phase)
                2'b00: next_phase = 2'b10;
                2'b10: next_phase = 2'b11;
                2'b11: next_phase = 2'b01;
                2'b01: next_phase = 2'b00;
                default: next_phase = 2'b00;
            endcase
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tick_count            <= 32'd0;
            revolution_edge_count <= 32'd0;
            phase                 <= 2'b00;
            enc_a                 <= 1'b0;
            enc_b                 <= 1'b0;
            enc_z                 <= 1'b0;
            position_edges        <= 32'd0;
        end else if (!enable) begin
            tick_count <= 32'd0;
            enc_z <= 1'b0;
        end else if (step_due) begin
            tick_count <= 32'd0;
            phase <= next_phase;
            enc_a <= next_phase[1];
            enc_b <= next_phase[0];

            if (direction_forward)
                position_edges <= position_edges + 32'd1;
            else
                position_edges <= position_edges - 32'd1;

            if (revolution_edge_count >= (COUNTS_PER_REV - 1)) begin
                revolution_edge_count <= 32'd0;
                enc_z <= 1'b1;
            end else begin
                revolution_edge_count <= revolution_edge_count + 32'd1;
                enc_z <= 1'b0;
            end
        end else begin
            tick_count <= tick_count + 32'd1;
        end
    end

endmodule

`default_nettype wire
