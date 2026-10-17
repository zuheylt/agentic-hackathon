// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CouncilRegistry {
    event TradeLogged(
        address indexed executor,
        string action,
        string tokenPair,
        uint256 amountUsd,
        string rationale,
        uint256 timestamp
    );

    function recordTrade(
        string memory action,
        string memory tokenPair,
        uint256 amountUsd,
        string memory rationale
    ) external {
        emit TradeLogged(
            msg.sender,
            action,
            tokenPair,
            amountUsd,
            rationale,
            block.timestamp
        );
    }
}