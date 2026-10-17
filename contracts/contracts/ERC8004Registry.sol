// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ERC8004Registry
 * @dev ERC-8004 Minimal Implementation for AI Agent Identity & Execution Logging
 */
contract ERC8004Registry {
    struct AgentCard {
        string name;
        string agentURI; // Agent Card JSON / IPFS link (ERC-8004 Identity)
        address owner;
        bool active;
    }

    struct TradeValidation {
        string action;
        string tokenPair;
        uint256 amountUsd;
        string rationale;
        uint256 timestamp;
        bool validated;
    }

    // Mapping for Agent Registration (ERC-8004 Identity Registry)
    mapping(uint256 => AgentCard) public agents;
    uint256 public agentCount;

    // Agent ID => Execution History (ERC-8004 Validation Registry)
    mapping(uint256 => TradeValidation[]) public agentValidations;

    event AgentRegistered(uint256 indexed agentId, string name, string agentURI, address owner);
    event ValidationRecorded(uint256 indexed agentId, string action, string tokenPair, uint256 amountUsd);

    function registerAgent(string memory name, string memory agentURI) external returns (uint256) {
        agentCount++;
        agents[agentCount] = AgentCard(name, agentURI, msg.sender, true);
        emit AgentRegistered(agentCount, name, agentURI, msg.sender);
        return agentCount;
    }

    function recordValidation(
        uint256 agentId,
        string memory action,
        string memory tokenPair,
        uint256 amountUsd,
        string memory rationale
    ) external {
        require(agents[agentId].active, "ERC8004: Agent is not registered/active");
        
        agentValidations[agentId].push(TradeValidation({
            action: action,
            tokenPair: tokenPair,
            amountUsd: amountUsd,
            rationale: rationale,
            timestamp: block.timestamp,
            validated: true
        }));

        emit ValidationRecorded(agentId, action, tokenPair, amountUsd);
    }
}