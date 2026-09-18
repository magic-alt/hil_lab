`default_nettype none

module abz_encoder_capture (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enc_a_async,
    input  wire        enc_b_async,
    input  wire        enc_z_async,
    input  wire [63:0] timestamp,
    input  wire        clear_faults,

    output reg  [31:0] position_edges,
    output reg         direction_forward,
    output reg         step_pulse,
    output reg         index_pulse,
    output reg         illegal_transition_latched,
    output reg  [63:0] last_edge_timestamp
);

    wire [2:0] enc_sync;
    wire [1:0] ab_now;
    wire       z_now;

    reg  [1:0] ab_prev;
    reg        z_prev;

    sync_2ff #(.WIDTH(3)) u_sync (
        .clk(clk),
        .rst_n(rst_n),
        .async_in({enc_z_async, enc_b_async, enc_a_async}),
        .sync_out(enc_sync)
    );

    assign ab_now = {enc_sync[0], enc_sync[1]};
    assign z_now  = enc_sync[2];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            position_edges              <= 32'd0;
            direction_forward           <= 1'b1;
            step_pulse                  <= 1'b0;
            index_pulse                 <= 1'b0;
            illegal_transition_latched  <= 1'b0;
            last_edge_timestamp         <= 64'd0;
            ab_prev                     <= 2'b00;
            z_prev                      <= 1'b0;
        end else begin
            step_pulse  <= 1'b0;
            index_pulse <= 1'b0;

            if (clear_faults)
                illegal_transition_latched <= 1'b0;

            if (z_now && !z_prev)
                index_pulse <= 1'b1;

            if (ab_now != ab_prev) begin
                last_edge_timestamp <= timestamp;
                case ({ab_prev, ab_now})
                    4'b0001,
                    4'b0111,
                    4'b1110,
                    4'b1000: begin
                        position_edges    <= position_edges + 32'd1;
                        direction_forward <= 1'b1;
                        step_pulse        <= 1'b1;
                    end

                    4'b0010,
                    4'b1011,
                    4'b1101,
                    4'b0100: begin
                        position_edges    <= position_edges - 32'd1;
                        direction_forward <= 1'b0;
                        step_pulse        <= 1'b1;
                    end

                    default: begin
                        illegal_transition_latched <= 1'b1;
                    end
                endcase
            end

            ab_prev <= ab_now;
            z_prev  <= z_now;
        end
    end

endmodule

`default_nettype wire
